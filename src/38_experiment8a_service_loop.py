"""Experiment 8A: software-only two-tier local service-loop benchmark.

The endpoint and transport in this experiment are explicitly simulated.  The
frozen Gate S2 int8 model is used at the gateway, but no physical acquisition,
hardware latency, energy, or clinical deployment claim is made.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import random
import tempfile
import threading
import time
from pathlib import Path
from typing import Callable

import numpy as np

from service_loop.endpoint_replay import ReplayEndpoint
from service_loop.contracts import SERVICE_CONTRACT_VERSION
from service_loop.gateway_ingest import GatewayIngest
from service_loop.gateway_inference import FrozenInt8Inference
from service_loop.gateway_policy import PolicyV1
from service_loop.gateway_signal import CausalSignalProcessor
from service_loop.gateway_store import GatewayStore
from service_loop.gateway_ingest import LocalGatewayRuntime
from service_loop.gateway_recovery import RecoveryManager
from service_loop.transport_mqtt import InMemoryTransport, LocalMqttV5Transport


POST_R_WAIT_MS = 416.6666667
DEFAULT_SEED = 20260810


def json_size(payload: dict) -> int:
    return len(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


class MeasuredTransport:
    """Measure a local transport and inject deterministic delivery faults."""

    def __init__(
        self,
        delegate,
        seed: int,
        loss_rate: float = 0.0,
        duplicate_rate: float = 0.0,
        reorder: bool = False,
        delay_ms: float = 0.0,
        unavailable: bool = False,
        drop_topics: set[str] | None = None,
        fail_topics: set[str] | None = None,
    ) -> None:
        self.delegate = delegate
        self.profile = getattr(delegate, "profile", "unknown")
        self.rng = random.Random(seed)
        self.loss_rate = loss_rate
        self.duplicate_rate = duplicate_rate
        self.reorder = reorder
        self.delay_ms = delay_ms
        self.unavailable = unavailable
        self.drop_topics = drop_topics or set()
        self.fail_topics = fail_topics or set()
        self._reorder_queue: list[tuple[str, dict]] = []
        self._lock = threading.Lock()
        self.stats = {
            "publish_calls": 0,
            "delivered_messages": 0,
            "dropped_messages": 0,
            "duplicate_messages": 0,
            "transport_failures": 0,
            "bytes_published": 0,
            "bytes_delivered": 0,
        }

    def subscribe(self, topic: str, callback: Callable[[dict], None]) -> None:
        self.delegate.subscribe(topic, callback)

    def publish(self, topic: str, payload: dict) -> None:
        payload_size = json_size(payload)
        self.stats["publish_calls"] += 1
        self.stats["bytes_published"] += payload_size
        if self.unavailable:
            self.stats["transport_failures"] += 1
            raise ConnectionError("simulated_local_link_outage")
        if topic in self.fail_topics:
            self.stats["transport_failures"] += 1
            raise ConnectionError("simulated_topic_delivery_failure")
        if topic in self.drop_topics or self.rng.random() < self.loss_rate:
            self.stats["dropped_messages"] += 1
            return
        deliveries = [payload]
        if self.rng.random() < self.duplicate_rate:
            deliveries.append(dict(payload))
            self.stats["duplicate_messages"] += 1
        if self.reorder:
            with self._lock:
                self._reorder_queue.extend((topic, item) for item in deliveries)
            return
        for item in deliveries:
            if self.delay_ms:
                time.sleep(self.delay_ms / 1000.0)
            self.delegate.publish(topic, item)
            self.stats["delivered_messages"] += 1
            self.stats["bytes_delivered"] += json_size(item)

    def flush_reorder(self) -> None:
        with self._lock:
            queued = list(self._reorder_queue)
            self._reorder_queue.clear()
        self.rng.shuffle(queued)
        for topic, payload in queued:
            self.delegate.publish(topic, payload)
            self.stats["delivered_messages"] += 1
            self.stats["bytes_delivered"] += json_size(payload)

    def close(self) -> None:
        close = getattr(self.delegate, "close", None)
        if close:
            close()


class LoopRunner:
    def __init__(self, manifest: Path, transport_kind: str, workdir: Path, seed: int = DEFAULT_SEED, **transport_options) -> None:
        self.manifest = manifest
        self.seed = seed
        self.workdir = workdir
        self.workdir.mkdir(parents=True, exist_ok=True)
        host = transport_options.pop("host", "127.0.0.1")
        port = int(transport_options.pop("port", 1883))
        if transport_kind == "mqtt":
            delegate = LocalMqttV5Transport(host, port)
        else:
            delegate = InMemoryTransport()
        fault_keys = {"loss_rate", "duplicate_rate", "reorder", "delay_ms", "unavailable", "drop_topics", "fail_topics"}
        fault_options = {key: value for key, value in transport_options.items() if key in fault_keys}
        self.transport = MeasuredTransport(delegate, seed=seed, **fault_options)
        self.store = GatewayStore(self.workdir / "gateway.sqlite")
        self.policy = PolicyV1()
        self.inference = FrozenInt8Inference(manifest)
        self.ingest = GatewayIngest("gateway-sim", self.inference.model_sha256, self.policy.version, self.store, self.policy)
        self.signal = CausalSignalProcessor(target_rate_hz=360)
        self.runtime = LocalGatewayRuntime(self.ingest, self.signal, self.inference, self.transport)
        self.endpoints: dict[str, ReplayEndpoint] = {}
        self.pending_acks: dict[str, threading.Event] = {}
        self.ack_times: dict[str, float] = {}
        self.ack_payloads: dict[str, dict] = {}
        self.transport_options = transport_options

    def add_endpoint(self, endpoint_id: str, buffer_capacity: int = 128) -> ReplayEndpoint:
        endpoint = ReplayEndpoint(endpoint_id, "gateway-sim", "two_channel", 360, self.inference.model_sha256, self.policy.version, buffer_capacity=buffer_capacity)
        self.endpoints[endpoint_id] = endpoint
        self.transport.subscribe(f"ecg/{endpoint_id}/ack", lambda payload, eid=endpoint_id: self._receive_ack(eid, payload))
        self.runtime.bind_endpoint(endpoint_id)
        return endpoint

    def _receive_ack(self, endpoint_id: str, payload: dict) -> None:
        received = time.perf_counter()
        self.ack_times[payload["event_id"]] = received
        self.ack_payloads[payload["event_id"]] = payload
        self.endpoints[endpoint_id].receive_ack(payload)
        event = self.pending_acks.get(payload["event_id"])
        if event:
            event.set()

    def send(self, endpoint: ReplayEndpoint, samples: list[list[float]], event_id: str | None = None, wait_ack: bool = True, timeout_s: float = 5.0) -> dict:
        packetization_started = time.perf_counter()
        packet = endpoint.packet(samples, event_id=event_id)
        packetization_ms = (time.perf_counter() - packetization_started) * 1000.0
        payload = packet.to_dict()
        started = time.perf_counter()
        event = threading.Event()
        self.pending_acks[packet.event_id] = event
        try:
            self.transport.publish(f"ecg/{endpoint.endpoint_id}/samples", payload)
            if wait_ack:
                event.wait(timeout_s)
        except Exception:
            pass
        finally:
            self.pending_acks.pop(packet.event_id, None)
        acked_at = self.ack_times.get(packet.event_id)
        return {
            "event_id": packet.event_id,
            "sample_sequence": packet.sample_sequence,
            "ack": self.ack_payloads.get(packet.event_id),
            "ack_latency_ms": ((acked_at - started) * 1000.0 if acked_at else None),
            "packet_bytes": json_size(payload),
            "packetization_ms": packetization_ms,
        }

    def close(self) -> None:
        self.transport.close()
        self.store.close()


def synthetic_samples(seed: int, count: int = 300) -> list[list[float]]:
    rng = np.random.default_rng(seed)
    t = np.arange(count, dtype=np.float32) / 360.0
    base = 0.08 * np.sin(2 * np.pi * 1.2 * t) + 0.02 * np.sin(2 * np.pi * 0.2 * t)
    spike = np.exp(-((np.arange(count) - count // 2) ** 2) / (2 * 4.0 ** 2)).astype(np.float32)
    noise = rng.normal(0.0, 0.01, size=count).astype(np.float32)
    ch1 = base + 1.4 * spike + noise
    ch2 = 0.7 * base + 1.0 * spike + rng.normal(0.0, 0.01, size=count).astype(np.float32)
    return np.column_stack((ch1, ch2)).astype(np.float32).tolist()


def run_baseline(runner: LoopRunner, sessions: int, windows: int) -> dict:
    rows = []
    for session in range(sessions):
        endpoint = runner.add_endpoint(f"endpoint-session-{session:03d}")
        for index in range(windows):
            rows.append(runner.send(endpoint, synthetic_samples(runner.seed + session * windows + index), event_id=f"session-{session:03d}-event-{index:04d}"))
    acknowledged = [row for row in rows if row["ack"] is not None]
    latencies = [row["ack_latency_ms"] for row in acknowledged if row["ack_latency_ms"] is not None]
    latencies.sort()
    pct = lambda p: latencies[min(len(latencies) - 1, int(round((len(latencies) - 1) * p)))] if latencies else None
    def component_summary(name: str, values: list[float]) -> dict[str, float | None]:
        ordered = sorted(values)
        choose = lambda p: ordered[min(len(ordered) - 1, int(round((len(ordered) - 1) * p)))] if ordered else None
        return {"p50": choose(0.50), "p95": choose(0.95), "p99": choose(0.99), "max": max(ordered) if ordered else None}

    packetization = [float(row["packetization_ms"]) for row in rows]
    accepted_metrics = [item for item in runner.runtime.metrics if item["ack_status"] == "accepted"]
    components = {
        name: component_summary(name, [float(item[name]) for item in accepted_metrics])
        for name in ("endpoint_to_gateway_ms", "signal_processing_ms", "neural_inference_ms", "policy_audit_ms", "acknowledgement_ms", "gateway_decision_ms", "gateway_total_ms")
    }
    components["endpoint_packetization_ms"] = component_summary("endpoint_packetization_ms", packetization)
    acquisition_to_decision = [
        POST_R_WAIT_MS + float(row["packetization_ms"]) + float(metric["endpoint_to_gateway_ms"]) + float(metric["gateway_decision_ms"])
        for row, metric in zip(rows, accepted_metrics)
        if row["ack"] is not None
    ]
    acquisition_to_ack = [POST_R_WAIT_MS + float(row["packetization_ms"]) + float(row["ack_latency_ms"]) for row in acknowledged]
    raw_reference_bytes = len(rows) * 300 * 2 * 2
    return {
        "sessions": sessions,
        "windows_sent": len(rows),
        "windows_acknowledged": len(acknowledged),
        "ack_success_rate": len(acknowledged) / len(rows) if rows else 0.0,
        "ack_latency_ms": {"p50": pct(0.50), "p95": pct(0.95), "p99": pct(0.99), "max": max(latencies) if latencies else None},
        "logical_post_r_wait_ms": POST_R_WAIT_MS,
        "logical_acquisition_to_decision_ms": component_summary("logical_acquisition_to_decision_ms", acquisition_to_decision),
        "logical_acquisition_to_ack_ms": component_summary("logical_acquisition_to_ack_ms", acquisition_to_ack),
        "latency_components_ms": components,
        "audit": runner.store.accepted_audit_completeness(),
        "rejected_reason_audit": runner.store.rejected_reason_completeness(),
        "transport": dict(runner.transport.stats),
        "endpoint_buffer_overflow": sum(endpoint.buffer_overflow_count for endpoint in runner.endpoints.values()),
        "bandwidth": {
            "local_loop_bytes_published": runner.transport.stats["bytes_published"],
            "continuous_raw_16bit_two_channel_reference_bytes": raw_reference_bytes,
            "optional_remote_egress_bytes": 0,
            "note": "Raw ECG remains on the simulated local link; no remote egress was enabled.",
        },
    }


def one_event(runner: LoopRunner, scenario: str, options: dict | None = None) -> dict:
    options = options or {}
    endpoint = runner.add_endpoint(f"endpoint-{scenario}", buffer_capacity=int(options.get("buffer_capacity", 128)))
    samples = synthetic_samples(runner.seed + 1)
    result: dict = {"scenario": scenario}
    if scenario == "duplicate":
        result["first"] = runner.send(endpoint, samples, event_id="duplicate-event")
        result["second"] = runner.send(endpoint, samples, event_id="duplicate-event")
    elif scenario == "out_of_order":
        packets = [endpoint.packet(synthetic_samples(runner.seed + i), event_id=f"reorder-{i}") for i in range(3)]
        for packet in (packets[0], packets[2], packets[1], packets[2]):
            result.setdefault("deliveries", []).append(runner.send_payload(endpoint, packet.to_dict()))
    elif scenario == "outage":
        runner.transport.unavailable = True
        for i in range(5):
            runner.send(endpoint, synthetic_samples(runner.seed + i), event_id=f"outage-{i}", wait_ack=False)
        buffered_before = len(endpoint.buffer)
        runner.transport.unavailable = False
        recovery_started = time.perf_counter()
        for packet in endpoint.retransmit():
            runner.send_payload(endpoint, packet.to_dict())
        recovery_time_ms = (time.perf_counter() - recovery_started) * 1000.0
        result["buffered_before_recovery"] = buffered_before
        result["remaining_buffer"] = len(endpoint.buffer)
        result["permanent_event_loss"] = len(endpoint.buffer)
        result["recovery_time_ms"] = recovery_time_ms
    elif scenario == "buffer_saturation":
        runner.transport.unavailable = True
        for i in range(int(options.get("events", 8))):
            runner.send(endpoint, synthetic_samples(runner.seed + i), event_id=f"saturation-{i}", wait_ack=False)
        result["buffer_overflow_count"] = endpoint.buffer_overflow_count
        result["buffer_size"] = len(endpoint.buffer)
        runner.transport.unavailable = False
    elif scenario == "delayed_ack":
        result["event"] = runner.send(endpoint, samples, event_id="delayed-ack")
    elif scenario == "malformed":
        bad = {"event_id": "malformed-event", "endpoint_id": endpoint.endpoint_id}
        result["event"] = runner.send_payload(endpoint, bad)
    elif scenario == "model_hash_mismatch":
        packet = endpoint.packet(samples, event_id="bad-model-hash").to_dict()
        packet["model_sha256"] = "0" * 64
        result["event"] = runner.send_payload(endpoint, packet)
    elif scenario == "poor_signal":
        result["event"] = runner.send(endpoint, [[0.0, 0.0]] * 300, event_id="poor-signal")
    elif scenario == "loss_recovery":
        runner.transport.loss_rate = float(options.get("loss_rate", 0.05))
        expected_events = int(options.get("events", 100))
        for i in range(expected_events):
            runner.send(endpoint, synthetic_samples(runner.seed + i), event_id=f"loss-{i}", timeout_s=0.02)
        initial_remaining = len(endpoint.buffer)
        runner.transport.loss_rate = 0.0
        recovery_started = time.perf_counter()
        for _ in range(5):
            pending = endpoint.retransmit()
            if not pending:
                break
            for packet in pending:
                runner.send_payload(endpoint, packet.to_dict())
        result["initial_remaining_buffer"] = initial_remaining
        result["remaining_buffer"] = len(endpoint.buffer)
        result["expected_events"] = expected_events
        result["accepted_events_after_recovery"] = runner.store.accepted_count()
        result["permanent_event_loss"] = expected_events - runner.store.accepted_count()
        result["recovery_time_ms"] = (time.perf_counter() - recovery_started) * 1000.0
        result["unresolved_latest_rejections"] = [
            {"event_id": row["event_id"], "response": json.loads(row["response_json"])}
            for row in runner.store.latest_events()
            if row["status"] == "rejected"
        ]
    elif scenario == "internet_outage":
        result["internet_available"] = False
        result["event"] = runner.send(endpoint, samples, event_id="internet-outage-local-loop")
    else:
        raise ValueError(f"unknown scenario: {scenario}")
    result["audit"] = runner.store.accepted_audit_completeness()
    result["rejected_reason_audit"] = runner.store.rejected_reason_completeness()
    result["transport"] = dict(runner.transport.stats)
    result["transport_callback_errors"] = list(getattr(runner.transport.delegate, "callback_errors", []))
    result["endpoint_buffer_overflow"] = endpoint.buffer_overflow_count
    return result


def _send_payload(self: LoopRunner, endpoint: ReplayEndpoint, payload: dict) -> dict:
    started = time.perf_counter()
    event = threading.Event()
    event_id = str(payload.get("event_id", "invalid"))
    self.pending_acks[event_id] = event
    try:
        self.transport.publish(f"ecg/{endpoint.endpoint_id}/samples", payload)
        event.wait(5.0)
    except Exception:
        pass
    finally:
        self.pending_acks.pop(event_id, None)
    acked_at = self.ack_times.get(event_id)
    return {"event_id": event_id, "ack": self.ack_payloads.get(event_id), "ack_latency_ms": ((acked_at - started) * 1000.0 if acked_at else None)}


LoopRunner.send_payload = _send_payload


def run_scenario(manifest: Path, transport_kind: str, scenario: str, seed: int, options: dict) -> dict:
    with tempfile.TemporaryDirectory(prefix=f"experiment8a_{scenario}_") as directory:
        runner = LoopRunner(manifest, transport_kind, Path(directory), seed=seed, **options)
        try:
            return one_event(runner, scenario, options)
        finally:
            runner.close()


def run_restart_scenario(manifest: Path, transport_kind: str, seed: int, host: str, port: int) -> dict:
    """Restart the gateway against the same WAL database and recover its ACK."""
    with tempfile.TemporaryDirectory(prefix="service_loop_restart_") as directory:
        db_dir = Path(directory)
        first = LoopRunner(manifest, transport_kind, db_dir, seed=seed, host=host, port=port, fail_topics={"ecg/endpoint-restart/ack"})
        endpoint = first.add_endpoint("endpoint-restart")
        first.send(endpoint, synthetic_samples(seed), event_id="restart-event", timeout_s=0.02)
        pending_before = len(first.store.pending_outbox())
        first.close()
        first_callback_errors = list(getattr(first.transport.delegate, "callback_errors", []))
        second = LoopRunner(manifest, transport_kind, db_dir, seed=seed + 1, host=host, port=port)
        endpoint2 = second.add_endpoint("endpoint-restart")
        endpoint2.sequence = second.ingest.next_sequence.get("endpoint-restart", 0)
        recovered = RecoveryManager(second.store, second.transport).recover()
        next_after_restart = second.send(endpoint2, synthetic_samples(seed + 2), event_id="restart-next-event")
        second_callback_errors = list(getattr(second.transport.delegate, "callback_errors", []))
        second.close()
        return {
            "pending_before_restart": pending_before,
            "recovery": recovered,
            "next_event_after_restart": next_after_restart,
            "event_loss": int(pending_before > 0 and recovered["delivered"] == 0),
            "transport_profile": "local_mqtt_v5_qos1" if transport_kind == "mqtt" else "simulated_in_memory_transport",
            "transport_callback_errors": first_callback_errors + second_callback_errors,
        }


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("results/gate_s2_int8_tf215_run1/manifest.json"))
    parser.add_argument("--output", type=Path, default=Path("results/experiment8a"))
    parser.add_argument("--transport", choices=("inmemory", "mqtt"), default="mqtt")
    parser.add_argument("--mqtt-host", default="127.0.0.1")
    parser.add_argument("--mqtt-port", type=int, default=1883)
    parser.add_argument("--broker-config", type=Path, default=Path("config/mosquitto-experiment.conf"))
    parser.add_argument("--sessions", type=int, default=30)
    parser.add_argument("--windows-per-session", type=int, default=40)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()
    manifest = args.manifest.resolve()
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    artifact = Path(manifest_data["artifacts"]["int8_tflite"])
    if not artifact.is_absolute() and not artifact.exists():
        artifact = manifest.parents[2] / artifact
    protocol = {
        "experiment": "8A",
        "status": "registered_execution",
        "evidence_class": "software-only simulated local digital service loop",
        "transport": {"kind": args.transport, "profile": "local_mqtt_v5_qos1" if args.transport == "mqtt" else "simulated_in_memory_transport", "mqtt_host": args.mqtt_host, "mqtt_port": args.mqtt_port, "broker_config": str(args.broker_config.resolve()), "broker_config_sha256": hashlib.sha256(args.broker_config.read_bytes()).hexdigest() if args.broker_config.exists() else None},
        "endpoint": {"id_pattern": "endpoint-session-NNN", "lead_profile": "two_channel", "native_sample_rate_hz": 360, "buffer_capacity": 128, "simulated_acquisition_endpoint": True},
        "gateway": {"id": "gateway-sim", "policy_version": "policy-v1", "gateway_sample_rate_hz": 360, "logical_post_r_wait_ms": POST_R_WAIT_MS},
        "service_contract": {"version": SERVICE_CONTRACT_VERSION, "compatibility_policy": "exact-version acceptance; mismatches are rejected and audited"},
        "model": {"manifest": str(manifest), "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(), "int8_artifact": str(artifact), "int8_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(), "threshold": manifest_data["calibration"]["threshold"]},
        "fault_seed": args.seed,
        "scenarios": ["duplicate", "out_of_order", "loss_recovery_1pct", "loss_recovery_5pct", "loss_recovery_10pct", "outage", "buffer_saturation", "delayed_ack", "malformed", "model_hash_mismatch", "poor_signal", "gateway_restart", "internet_outage"],
        "external_data_accessed": False,
        "physical_hardware_used": False,
    }
    write_json(args.output / "protocol.json", protocol)

    baseline_dir = Path(tempfile.mkdtemp(prefix="experiment8a_baseline_"))
    baseline_runner = LoopRunner(manifest, args.transport, baseline_dir, seed=args.seed, host=args.mqtt_host, port=args.mqtt_port)
    try:
        baseline = run_baseline(baseline_runner, args.sessions, args.windows_per_session)
        baseline["model_inference_latency_ms"] = getattr(baseline_runner.inference, "last_latency_ms", None)
        baseline["transport_profile"] = baseline_runner.transport.profile
        baseline["transport_callback_errors"] = list(getattr(baseline_runner.transport.delegate, "callback_errors", []))
    finally:
        baseline_runner.close()

    scenario_results = {}
    scenario_results["duplicate"] = run_scenario(manifest, args.transport, "duplicate", args.seed + 1, {"host": args.mqtt_host, "port": args.mqtt_port})
    scenario_results["out_of_order"] = run_scenario(manifest, args.transport, "out_of_order", args.seed + 2, {"host": args.mqtt_host, "port": args.mqtt_port})
    for index, rate in enumerate((0.01, 0.05, 0.10), start=3):
        scenario_results[f"loss_recovery_{int(rate * 100)}pct"] = run_scenario(manifest, args.transport, "loss_recovery", args.seed + index, {"host": args.mqtt_host, "port": args.mqtt_port, "loss_rate": rate, "events": 100})
    for index, scenario in enumerate(("outage", "buffer_saturation", "delayed_ack", "malformed", "model_hash_mismatch", "poor_signal", "internet_outage"), start=6):
        options = {"host": args.mqtt_host, "port": args.mqtt_port}
        if scenario == "buffer_saturation":
            options.update({"buffer_capacity": 4, "events": 8})
        if scenario == "delayed_ack":
            options["delay_ms"] = 25.0
        scenario_results[scenario] = run_scenario(manifest, args.transport, scenario, args.seed + index, options)

    # Restart is run with a durable database and a gateway ACK outage.  The
    # second gateway instance must recover the queued ACK from SQLite WAL.
    scenario_results["gateway_restart"] = run_restart_scenario(manifest, args.transport, args.seed + 20, args.mqtt_host, args.mqtt_port)

    accepted = baseline["windows_acknowledged"]
    duplicate_actions = int(scenario_results["duplicate"].get("audit", {}).get("accepted_events", 0) > 1)
    recovery_loss = {name: value.get("permanent_event_loss", value.get("remaining_buffer")) for name, value in scenario_results.items() if name.startswith("loss_recovery_") or name == "outage"}
    summary = {
        "experiment": "8A",
        "status": "completed",
        "evidence_class": "software-only simulated local digital service loop",
        "transport_profile": baseline["transport_profile"],
        "service_contract_version": SERVICE_CONTRACT_VERSION,
        "model_sha256": manifest_data["artifacts"]["int8_tflite_sha256"],
        "threshold": manifest_data["calibration"]["threshold"],
        "policy_version": "policy-v1",
        "baseline": baseline,
        "scenarios": scenario_results,
        "acceptance": {
            "zero_duplicate_actions": duplicate_actions == 0,
            "zero_permanent_event_loss_after_recovery": all(value in (0, None) for value in recovery_loss.values()) and scenario_results["gateway_restart"].get("event_loss") == 0,
            "accepted_audit_completeness_100pct": baseline["audit"]["completeness"] == 1.0,
            "rejected_reason_completeness_100pct": all(result.get("rejected_reason_audit", {}).get("completeness", 1.0) == 1.0 for result in scenario_results.values()),
            "local_loop_survives_internet_outage": scenario_results["internet_outage"].get("event", {}).get("ack", {}).get("ack_status") == "accepted",
            "gateway_restart_recovers_wal_outbox": scenario_results["gateway_restart"].get("pending_before_restart", 0) > 0 and scenario_results["gateway_restart"].get("recovery", {}).get("delivered", 0) > 0,
            "no_transport_callback_errors": not baseline["transport_callback_errors"] and all(not result.get("transport_callback_errors", []) for result in scenario_results.values()),
        },
        "service_metrics": {
            "successful_terminal_action_rate": baseline["windows_acknowledged"] / baseline["windows_sent"] if baseline["windows_sent"] else 0.0,
            "duplicate_action_rate": duplicate_actions / 1.0,
            "permanent_event_loss_after_recovery": recovery_loss,
            "recovery_time_ms": {name: value.get("recovery_time_ms") for name, value in scenario_results.items() if name.startswith("loss_recovery_") or name == "outage"},
            "accepted_audit_completeness": baseline["audit"]["completeness"],
        },
        "model_or_threshold_changed": False,
        "external_data_accessed": False,
        "host": {"platform": platform.platform(), "python": platform.python_version(), "pid": os.getpid()},
    }
    write_json(args.output / "summary.json", summary)
    with (args.output / "runs.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=("scenario", "status", "accepted_events", "rejected_events", "audit_completeness", "rejected_reason_completeness", "bytes_published", "bytes_delivered"))
        writer.writeheader()
        writer.writerow({"scenario": "baseline", "status": "completed", "accepted_events": baseline["windows_acknowledged"], "rejected_events": 0, "audit_completeness": baseline["audit"]["completeness"], "rejected_reason_completeness": baseline["rejected_reason_audit"]["completeness"], "bytes_published": baseline["transport"]["bytes_published"], "bytes_delivered": baseline["transport"]["bytes_delivered"]})
        for name, result in scenario_results.items():
            writer.writerow({"scenario": name, "status": "completed", "accepted_events": result.get("audit", {}).get("accepted_events", ""), "rejected_events": result.get("rejected_reason_audit", {}).get("rejected_attempts", ""), "audit_completeness": result.get("audit", {}).get("completeness", ""), "rejected_reason_completeness": result.get("rejected_reason_audit", {}).get("completeness", ""), "bytes_published": result.get("transport", {}).get("bytes_published", ""), "bytes_delivered": result.get("transport", {}).get("bytes_delivered", "")})
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
