"""Experiment 7: software gateway runtime and local-loop benchmark.

All measurements are development-host software measurements.  They do not
represent physical ECG acquisition, wearable hardware, MCU latency, or energy.
"""

from __future__ import annotations

import argparse
import csv
import ctypes
import hashlib
import importlib.util
import json
import os
import platform
import statistics
import tempfile
import threading
import time
from pathlib import Path


def load_experiment8a_module():
    path = Path(__file__).with_name("38_experiment8a_service_loop.py")
    spec = importlib.util.spec_from_file_location("experiment8a_runtime", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Experiment 8A runtime module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def percentile_summary(values: list[float]) -> dict[str, float | None]:
    ordered = sorted(values)
    if not ordered:
        return {"p50": None, "p95": None, "p99": None, "max": None, "mean": None}
    choose = lambda p: ordered[min(len(ordered) - 1, int(round((len(ordered) - 1) * p)))]
    return {"p50": choose(0.50), "p95": choose(0.95), "p99": choose(0.99), "max": max(ordered), "mean": statistics.fmean(ordered)}


def process_rss_bytes() -> int:
    if os.name == "nt":
        from ctypes import wintypes

        class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
                ("PrivateUsage", ctypes.c_size_t),
            ]
        counters = PROCESS_MEMORY_COUNTERS_EX()
        counters.cb = ctypes.sizeof(counters)
        ctypes.windll.kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        ctypes.windll.psapi.GetProcessMemoryInfo.argtypes = (wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD)
        ctypes.windll.psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        if not ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
            raise OSError("GetProcessMemoryInfo failed")
        return int(counters.WorkingSetSize)
    import resource
    maximum = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(maximum * (1024 if platform.system() != "Darwin" else 1))


class MemorySampler:
    def __init__(self, interval_s: float = 0.01) -> None:
        self.interval_s = interval_s
        self.samples: list[int] = []
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self.stop_event.is_set():
            try:
                self.samples.append(process_rss_bytes())
            except OSError:
                pass
            self.stop_event.wait(self.interval_s)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, _type, _value, _traceback) -> None:
        self.stop_event.set()
        self.thread.join(timeout=2.0)
        try:
            self.samples.append(process_rss_bytes())
        except OSError:
            pass


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("results/gate_s2_int8_tf215_run1/manifest.json"))
    parser.add_argument("--experiment8a-summary", type=Path, default=Path("results/experiment8a/summary.json"))
    parser.add_argument("--output", type=Path, default=Path("results/experiment7"))
    parser.add_argument("--transport", choices=("inmemory", "mqtt"), default="mqtt")
    parser.add_argument("--mqtt-host", default="127.0.0.1")
    parser.add_argument("--mqtt-port", type=int, default=1883)
    parser.add_argument("--inference-windows", type=int, default=1020)
    parser.add_argument("--sessions", type=int, default=30)
    parser.add_argument("--warmup-windows", type=int, default=50)
    parser.add_argument("--seed", type=int, default=20260810)
    args = parser.parse_args()
    if args.inference_windows < 1000:
        raise ValueError("Experiment 7 requires at least 1,000 inference windows")
    if args.sessions < 30:
        raise ValueError("Experiment 7 requires at least 30 complete sessions")
    if not args.experiment8a_summary.exists():
        raise FileNotFoundError("Experiment 8A must complete before Experiment 7")

    exp8 = load_experiment8a_module()
    manifest = args.manifest.resolve()
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    eight_summary = json.loads(args.experiment8a_summary.read_text(encoding="utf-8"))
    expected_profile = "local_mqtt_v5_qos1" if args.transport == "mqtt" else "simulated_in_memory_transport"
    if eight_summary.get("transport_profile") != expected_profile:
        raise ValueError("Experiment 7 transport must match the completed Experiment 8A profile")
    artifact = Path(manifest_data["artifacts"]["int8_tflite"])
    if not artifact.is_absolute() and not artifact.exists():
        artifact = manifest.parents[2] / artifact
    protocol = {
        "experiment": "7",
        "status": "registered_execution",
        "evidence_class": "development-host software runtime",
        "sessions": args.sessions,
        "inference_windows": args.inference_windows,
        "warmup_windows": args.warmup_windows,
        "transport_profile": expected_profile,
        "logical_clock": "single-host time.perf_counter_ns monotonic clock",
        "mandatory_post_r_wait_ms": exp8.POST_R_WAIT_MS,
        "model": {"manifest": str(manifest), "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(), "int8_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(), "threshold": manifest_data["calibration"]["threshold"]},
        "service_contract_version": exp8.SERVICE_CONTRACT_VERSION,
        "policy_version": "policy-v1",
        "same_fault_profile_as_experiment8a": True,
        "physical_hardware_used": False,
        "energy_measured": False,
    }
    write_json(args.output / "protocol.json", protocol)

    with tempfile.TemporaryDirectory(prefix="experiment7_warmup_") as directory:
        warmup = exp8.LoopRunner(manifest, args.transport, Path(directory), seed=args.seed, host=args.mqtt_host, port=args.mqtt_port)
        endpoint = warmup.add_endpoint("endpoint-warmup")
        for index in range(args.warmup_windows):
            warmup.send(endpoint, exp8.synthetic_samples(args.seed + index), event_id=f"warmup-{index}")
        warmup.close()

    runtime_dir = Path(tempfile.mkdtemp(prefix="experiment7_runtime_"))
    runner = exp8.LoopRunner(manifest, args.transport, runtime_dir, seed=args.seed + 1000, host=args.mqtt_host, port=args.mqtt_port)
    endpoints = [runner.add_endpoint(f"endpoint-runtime-{index:03d}") for index in range(args.sessions)]
    rows: list[dict] = []
    cpu_started = time.process_time()
    wall_started = time.perf_counter()
    with MemorySampler() as memory:
        for index in range(args.inference_windows):
            endpoint = endpoints[index % args.sessions]
            rows.append(runner.send(endpoint, exp8.synthetic_samples(args.seed + 2000 + index), event_id=f"runtime-{index:05d}"))
    wall_seconds = time.perf_counter() - wall_started
    cpu_seconds = time.process_time() - cpu_started
    metrics = [item for item in runner.runtime.metrics if item["ack_status"] == "accepted"]
    audit = runner.store.accepted_audit_completeness()
    rejected_audit = runner.store.rejected_reason_completeness()
    transport_stats = dict(runner.transport.stats)
    transport_callback_errors = list(getattr(runner.transport.delegate, "callback_errors", []))
    runner.close()

    accepted_rows = [row for row in rows if row["ack"] and row["ack"]["ack_status"] == "accepted"]
    component_names = ("endpoint_to_gateway_ms", "signal_processing_ms", "neural_inference_ms", "policy_audit_ms", "acknowledgement_ms", "gateway_decision_ms", "gateway_total_ms")
    components = {name: percentile_summary([float(item[name]) for item in metrics]) for name in component_names}
    components["endpoint_packetization_ms"] = percentile_summary([float(row["packetization_ms"]) for row in accepted_rows])
    components["endpoint_to_gateway_to_endpoint_ack_ms"] = percentile_summary([float(row["ack_latency_ms"]) for row in accepted_rows])
    acquisition_to_decision = [
        exp8.POST_R_WAIT_MS + float(row["packetization_ms"]) + float(metric["endpoint_to_gateway_ms"]) + float(metric["gateway_decision_ms"])
        for row, metric in zip(accepted_rows, metrics)
    ]
    acquisition_to_ack = [exp8.POST_R_WAIT_MS + float(row["packetization_ms"]) + float(row["ack_latency_ms"]) for row in accepted_rows]
    components["logical_acquisition_to_local_decision_ms"] = percentile_summary(acquisition_to_decision)
    components["logical_acquisition_to_endpoint_ack_ms"] = percentile_summary(acquisition_to_ack)

    # Repeat the bounded transport fault family used by 8A on the same profile.
    faults = {
        "duplicate": exp8.run_scenario(manifest, args.transport, "duplicate", args.seed + 3001, {"host": args.mqtt_host, "port": args.mqtt_port}),
        "out_of_order": exp8.run_scenario(manifest, args.transport, "out_of_order", args.seed + 3002, {"host": args.mqtt_host, "port": args.mqtt_port}),
        "outage": exp8.run_scenario(manifest, args.transport, "outage", args.seed + 3003, {"host": args.mqtt_host, "port": args.mqtt_port}),
    }
    for offset, rate in enumerate((0.01, 0.05, 0.10), start=4):
        faults[f"loss_recovery_{int(rate * 100)}pct"] = exp8.run_scenario(manifest, args.transport, "loss_recovery", args.seed + 3000 + offset, {"host": args.mqtt_host, "port": args.mqtt_port, "loss_rate": rate, "events": 100})
    faults["gateway_restart"] = exp8.run_restart_scenario(manifest, args.transport, args.seed + 3010, args.mqtt_host, args.mqtt_port)
    fault_callback_errors = {name: result.get("transport_callback_errors", []) for name, result in faults.items() if result.get("transport_callback_errors", [])}

    model_size = artifact.stat().st_size
    process_cpu_one_core_percent = 100.0 * cpu_seconds / wall_seconds if wall_seconds else 0.0
    cpu_count = os.cpu_count() or 1
    summary = {
        "experiment": "7",
        "status": "completed",
        "evidence_class": "development-host software runtime",
        "transport_profile": expected_profile,
        "service_contract_version": exp8.SERVICE_CONTRACT_VERSION,
        "model_sha256": manifest_data["artifacts"]["int8_tflite_sha256"],
        "threshold": manifest_data["calibration"]["threshold"],
        "policy_version": "policy-v1",
        "sessions": args.sessions,
        "requested_windows": args.inference_windows,
        "accepted_inference_windows": len(accepted_rows),
        "latency_components_ms": components,
        "resources": {
            "model_size_bytes": model_size,
            "peak_process_resident_memory_bytes": max(memory.samples) if memory.samples else None,
            "process_cpu_time_seconds": cpu_seconds,
            "wall_time_seconds": wall_seconds,
            "process_cpu_percent_one_core_equivalent": process_cpu_one_core_percent,
            "process_cpu_percent_host_normalized": process_cpu_one_core_percent / cpu_count,
            "logical_cpu_count": cpu_count,
            "accepted_windows_per_second": len(accepted_rows) / wall_seconds if wall_seconds else None,
            "messages_per_second": transport_stats["delivered_messages"] / wall_seconds if wall_seconds else None,
        },
        "transport": transport_stats,
        "transport_callback_errors": transport_callback_errors,
        "audit": audit,
        "rejected_reason_audit": rejected_audit,
        "fault_replay": faults,
        "fault_transport_callback_errors": fault_callback_errors,
        "targets": {
            "int8_model_under_1_mib": model_size < 1024 * 1024,
            "p95_neural_inference_under_50_ms": components["neural_inference_ms"]["p95"] is not None and components["neural_inference_ms"]["p95"] < 50.0,
            "p95_acquisition_to_local_decision_under_600_ms": components["logical_acquisition_to_local_decision_ms"]["p95"] is not None and components["logical_acquisition_to_local_decision_ms"]["p95"] < 600.0,
            "accepted_audit_completeness_100pct": audit["completeness"] == 1.0,
            "at_least_1000_inference_windows": len(accepted_rows) >= 1000,
            "at_least_30_sessions": args.sessions >= 30,
            "no_transport_callback_errors": not transport_callback_errors and not fault_callback_errors,
        },
        "host": {"platform": platform.platform(), "python": platform.python_version(), "processor": platform.processor()},
        "disclaimer": "Software-runtime measurements on the declared development host; not physical acquisition, hardware latency, energy, MCU, wearable, clinical efficacy, or regulatory evidence.",
        "model_or_threshold_changed": False,
        "external_data_accessed": False,
    }
    write_json(args.output / "summary.json", summary)
    with (args.output / "latency_samples.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ("event_id", "packetization_ms", "ack_latency_ms", *component_names)
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row, metric in zip(accepted_rows, metrics):
            writer.writerow({"event_id": row["event_id"], "packetization_ms": row["packetization_ms"], "ack_latency_ms": row["ack_latency_ms"], **{name: metric[name] for name in component_names}})
    print(json.dumps({"experiment": "7", "status": "completed", "targets": summary["targets"], "resources": summary["resources"], "latency_components_ms": components}, indent=2))


if __name__ == "__main__":
    main()
