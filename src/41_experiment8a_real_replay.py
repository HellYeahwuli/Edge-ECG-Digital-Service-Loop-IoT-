"""Post-Gate-V exploratory real-ECG replay over the frozen local MQTT loop.

This strengthens input realism only. It does not revise Gate V or evaluate
clinical classification accuracy; the endpoint is still software simulated.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import tempfile
from fractions import Fraction
from pathlib import Path

import numpy as np
import wfdb
from scipy.signal import resample_poly


RECORDS = (("mitdb", "100"), ("mitdb", "101"), ("mitdb", "103"),
           ("mitdb", "105"), ("mitdb", "106"), ("incartdb", "I01"),
           ("incartdb", "I02"), ("incartdb", "I03"), ("incartdb", "I04"),
           ("incartdb", "I05"))
WINDOWS_PER_SESSION = 30
WINDOW_SAMPLES = 300
START_NATIVE_SAMPLE = 10000
MODEL_SHA256 = "edea13aacdd5f6f9f94a3b73092f567f25b4dcade6133da4af7eb42aa2913776"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def experiment8a_module():
    source = Path(__file__).with_name("38_experiment8a_service_loop.py")
    spec = importlib.util.spec_from_file_location("experiment8a_real_replay_base", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("Experiment 8A runner unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_files(data_root: Path, source: str, name: str) -> list[Path]:
    base = data_root / source / name
    header = base.with_suffix(".hea")
    if not header.exists():
        raise FileNotFoundError(header)
    files = [header]
    for line in header.read_text(encoding="latin-1").splitlines()[1:]:
        if line.startswith("#"):
            continue
        filename = line.split()[0]
        path = header.parent / filename
        if path not in files:
            files.append(path)
    for path in files:
        if not path.exists():
            raise FileNotFoundError(path)
    return files


def fixed_fragment(data_root: Path, source: str, name: str) -> tuple[np.ndarray, dict]:
    base = data_root / source / name
    header = wfdb.rdheader(str(base))
    if source == "incartdb":
        channel_names = ("II", "V1")
        if not all(channel in header.sig_name for channel in channel_names):
            raise ValueError(f"missing fixed INCART channels: {name}")
        channels = [header.sig_name.index(channel) for channel in channel_names]
    else:
        channels = [header.sig_name.index("MLII") if "MLII" in header.sig_name else 0]
        channels += [next(index for index in range(header.n_sig) if index != channels[0])]
        channel_names = tuple(header.sig_name[index] for index in channels)
    ratio = Fraction(360 / header.fs).limit_denominator(10000)
    native_count = int(np.ceil(WINDOWS_PER_SESSION * WINDOW_SAMPLES * header.fs / 360)) + 2
    record = wfdb.rdrecord(str(base), sampfrom=START_NATIVE_SAMPLE,
                           sampto=START_NATIVE_SAMPLE + native_count, channels=channels)
    samples = resample_poly(record.p_signal, ratio.numerator, ratio.denominator, axis=0)
    samples = np.asarray(samples[:WINDOWS_PER_SESSION * WINDOW_SAMPLES], dtype=np.float32)
    if samples.shape != (WINDOWS_PER_SESSION * WINDOW_SAMPLES, 2) or not np.isfinite(samples).all():
        raise ValueError(f"invalid fixed fragment: {source}:{name}")
    metadata = {"source": source, "record": name, "native_sample_rate_hz": header.fs,
                "native_start_sample": START_NATIVE_SAMPLE, "native_sample_count": native_count,
                "native_channels": list(channel_names), "gateway_sample_rate_hz": 360,
                "gateway_sample_count": len(samples),
                "source_files_sha256": {str(path.relative_to(data_root)): sha256(path)
                                        for path in source_files(data_root, source, name)}}
    return samples, metadata


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict:
    base = experiment8a_module()
    manifest = args.manifest.resolve()
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    if manifest_data["artifacts"]["int8_tflite_sha256"] != MODEL_SHA256:
        raise ValueError("frozen model mismatch")
    if float(manifest_data["calibration"]["threshold"]) != 0.49:
        raise ValueError("frozen threshold mismatch")
    fragments = [fixed_fragment(args.data_root, source, name) for source, name in RECORDS]
    protocol = {
        "experiment": "8A real ECG replay strengthening", "status": "registered_execution",
        "evidence_class": "post-Gate-V exploratory software-simulated real-data replay",
        "source_role": "MIT-BIH and INCART development sources; no SVDB or NSRDB access",
        "selection": "first fixed fragment at native sample 10000 from five named records per source",
        "fragments": [metadata for _, metadata in fragments],
        "sessions": len(fragments), "windows_per_session": WINDOWS_PER_SESSION,
        "samples_per_window": WINDOW_SAMPLES, "resampling": "scipy.signal.resample_poly",
        "transport_profile": "local_mqtt_v5_qos1", "mqtt_host": args.mqtt_host,
        "mqtt_port": args.mqtt_port, "lead_profile": "two_channel",
        "policy_version": "policy-v1", "service_contract_version": base.SERVICE_CONTRACT_VERSION,
        "model_sha256": MODEL_SHA256, "threshold": 0.49,
        "model_manifest_sha256": sha256(manifest),
        "r_peak_method": "gateway packet-local maximum-amplitude proxy; not Experiment 5 causal detector",
        "primary_8a_or_gate_v_changed": False,
        "clinical_accuracy_claim": False, "physical_acquisition_claim": False,
    }
    write_json(args.output / "protocol.json", protocol)
    rows = []
    with tempfile.TemporaryDirectory(prefix="experiment8a_real_replay_") as directory:
        runner = base.LoopRunner(manifest, "mqtt", Path(directory), host=args.mqtt_host, port=args.mqtt_port)
        try:
            for samples, metadata in fragments:
                endpoint_id = f"endpoint-real-{metadata['source']}-{metadata['record']}"
                endpoint = runner.add_endpoint(endpoint_id)
                for index in range(WINDOWS_PER_SESSION):
                    start = index * WINDOW_SAMPLES
                    result = runner.send(endpoint, samples[start:start + WINDOW_SAMPLES].tolist(),
                                         event_id=f"real-{metadata['source']}-{metadata['record']}-{index:02d}")
                    ack = result["ack"] or {}
                    rows.append({"source": metadata["source"], "record": metadata["record"],
                                 "window_index": index, "event_id": result["event_id"],
                                 "sample_sequence": result["sample_sequence"],
                                 "window_formed": ack.get("ack_status") == "accepted",
                                 "r_peak_status": "packet_local_proxy" if ack.get("ack_status") == "accepted" else "not_formed",
                                 "ack_status": ack.get("ack_status", "missing"),
                                 "requested_action": ack.get("requested_action", ""),
                                 "reason": ack.get("reason", ""),
                                 "terminal_status": ack.get("terminal_status", ""),
                                 "ack_latency_ms": result["ack_latency_ms"]})
            events = runner.store.latest_events()
            signal_quality = {}
            for item in events:
                if item["status"] == "accepted":
                    payload = json.loads(item["payload_json"])
                    signal_quality[item["event_id"]] = payload["event"]["signal_quality"]
            for row in rows:
                row["signal_quality"] = signal_quality.get(row["event_id"])
            audit = runner.store.accepted_audit_completeness()
            rejected = runner.store.rejected_reason_completeness()
            transport = dict(runner.transport.stats)
            callback_errors = list(runner.transport.delegate.callback_errors)
        finally:
            runner.close()
    with (args.output / "events.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    accepted = sum(row["ack_status"] == "accepted" for row in rows)
    summary = {
        "experiment": protocol["experiment"], "status": "completed",
        "evidence_class": protocol["evidence_class"], "sessions": len(fragments),
        "windows_sent": len(rows), "windows_accepted": accepted,
        "window_formation_rate": accepted / len(rows),
        "r_peak_proxy_status_recorded": all(row["r_peak_status"] == "packet_local_proxy" for row in rows if row["window_formed"]),
        "actions": {action: sum(row["requested_action"] == action for row in rows)
                    for action in sorted({row["requested_action"] for row in rows})},
        "acknowledged": sum(row["ack_status"] != "missing" for row in rows),
        "accepted_audit": audit, "rejected_reason_audit": rejected,
        "transport": transport, "transport_callback_errors": callback_errors,
        "model_sha256": MODEL_SHA256, "threshold": 0.49,
        "policy_version": "policy-v1", "service_contract_version": base.SERVICE_CONTRACT_VERSION,
        "transport_profile": "local_mqtt_v5_qos1",
        "acceptance": {"at_least_10_fragments": len(fragments) >= 10,
                       "at_least_300_windows": len(rows) >= 300,
                       "at_least_10_sessions": len(fragments) >= 10,
                       "accepted_audit_completeness_100pct": audit["completeness"] == 1.0,
                       "rejected_reason_completeness_100pct": rejected["completeness"] == 1.0,
                       "no_transport_callback_errors": not callback_errors},
        "claim_boundary": "Real public ECG input to a simulated local MQTT loop using a packet-local peak proxy; not Experiment 5 detector accuracy, physical acquisition, or clinical validation.",
    }
    write_json(args.output / "summary.json", summary)
    if not all(summary["acceptance"].values()):
        raise AssertionError("real replay acceptance failed")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument("--manifest", type=Path, default=Path("results/gate_s2_int8_tf215_run1/manifest.json"))
    parser.add_argument("--output", type=Path, default=Path("results/experiment8a_real_replay"))
    parser.add_argument("--mqtt-host", default="127.0.0.1")
    parser.add_argument("--mqtt-port", type=int, default=1883)
    args = parser.parse_args()
    print(json.dumps(run(args), indent=2))


if __name__ == "__main__":
    main()
