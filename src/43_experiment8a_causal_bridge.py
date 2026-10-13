"""Registered exploratory causal R-peak to MQTT service-loop bridge.

The public ECG fragment is resampled before MQTT transmission. This is a
software replay, not a causal native-rate acquisition or a Gate V rerun.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import sys
import threading
import time
from pathlib import Path

import numpy as np

from multisource_ecg import normalise_window
from service_loop.contracts import ECGPacket, GatewayEvent, SERVICE_CONTRACT_VERSION, utc_now
from service_loop.gateway_ingest import GatewayIngest
from service_loop.gateway_inference import FrozenInt8Inference
from service_loop.gateway_policy import PolicyV1
from service_loop.gateway_store import GatewayStore
from service_loop.transport_mqtt import LocalMqttV5Transport


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "results" / "experiment8a_causal_bridge"
MANIFEST = ROOT / "results" / "gate_s2_int8_tf215_run1" / "manifest.json"
SOURCE_PROTOCOL = ROOT / "results" / "experiment8a_real_replay" / "protocol.json"
MODEL_SHA256 = "edea13aacdd5f6f9f94a3b73092f567f25b4dcade6133da4af7eb42aa2913776"
CHUNK_SAMPLES = 180
WINDOW_SAMPLES = 300
HALF_WINDOW = 150
SAMPLE_RATE = 360
MATCH_TOLERANCE_SAMPLES = 54
DROP_START = 10 * SAMPLE_RATE
DROP_STOP = 15 * SAMPLE_RATE
SOURCE_FILES = (
    "src/06_evaluate_streaming_rpeaks.py",
    "src/34_experiment5_oracle_automatic_rpeaks.py",
    "src/41_experiment8a_real_replay.py",
    "src/43_experiment8a_causal_bridge.py",
    "src/multisource_ecg.py",
    "src/service_loop/contracts.py",
    "src/service_loop/gateway_ingest.py",
    "src/service_loop/gateway_inference.py",
    "src/service_loop/gateway_policy.py",
    "src/service_loop/gateway_store.py",
    "src/service_loop/transport_mqtt.py",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


detector = load_module(ROOT / "src" / "06_evaluate_streaming_rpeaks.py", "bridge_frozen_detector")
experiment5 = load_module(ROOT / "src" / "34_experiment5_oracle_automatic_rpeaks.py", "bridge_experiment5")
real_replay = load_module(ROOT / "src" / "41_experiment8a_real_replay.py", "bridge_real_replay")


def write_json_once(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite registered artifact: {path}")
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def frozen_inputs() -> tuple[dict, dict]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    original = json.loads(SOURCE_PROTOCOL.read_text(encoding="utf-8"))
    if manifest["status"] != "passed" or manifest["artifacts"]["int8_tflite_sha256"] != MODEL_SHA256:
        raise ValueError("frozen_model_mismatch")
    if float(manifest["calibration"]["threshold"]) != 0.49:
        raise ValueError("frozen_threshold_mismatch")
    if original["model_sha256"] != MODEL_SHA256 or original["policy_version"] != "policy-v1":
        raise ValueError("source_replay_configuration_mismatch")
    return manifest, original


def register(data_root: Path, output: Path) -> None:
    _, original = frozen_inputs()
    fixed = []
    for row in original["fragments"]:
        samples, metadata = real_replay.fixed_fragment(data_root, row["source"], row["record"])
        if metadata != row or samples.shape != (9000, 2):
            raise ValueError(f"fixed_fragment_mismatch:{row['source']}:{row['record']}")
        fixed.append(row)
    protocol = {
        "experiment": "8A causal-detector-to-MQTT bridge",
        "status": "registered_before_execution",
        "evidence_class": "post-Gate-V exploratory software replay on development sources",
        "registration_utc": utc_now(),
        "source_replay_protocol_sha256": sha256(SOURCE_PROTOCOL),
        "manifest_sha256": sha256(MANIFEST),
        "source_code_sha256": {name: sha256(ROOT / name) for name in SOURCE_FILES},
        "fragments": fixed,
        "fragment_order": [f"{row['source']}:{row['record']}" for row in fixed],
        "preprocessing": "The existing 41_experiment8a_real_replay.py fixed_fragment uses scipy.signal.resample_poly on each complete fixed fragment before MQTT. This bridge does not establish native-rate causal preprocessing.",
        "endpoint": {"simulated": True, "gateway_sample_rate_hz": SAMPLE_RATE, "lead_profile": "two_channel", "chunk_samples": CHUNK_SAMPLES, "source_sequence_starts_at": 0},
        "gateway": {"detector": "unchanged causal_pan_tompkins from src/06_evaluate_streaming_rpeaks.py, repeatedly applied to the received prefix after a fixed 720-sample initialization", "detector_state_reset": "each fixed record/scenario boundary", "window_samples": WINDOW_SAMPLES, "post_r_samples": HALF_WINDOW, "post_r_wait_ms": 1000 * HALF_WINDOW / SAMPLE_RATE, "rr": "unchanged Experiment 5 rr_features", "normalization": "unchanged per-window per-channel normalization from multisource_ecg.normalise_window", "repeated_prefix_cost_measured_separately": True},
        "model_sha256": MODEL_SHA256,
        "threshold": 0.49,
        "policy_version": "policy-v1",
        "service_contract_version": SERVICE_CONTRACT_VERSION,
        "transport_profile": "local_mqtt_v5_qos1",
        "mqtt_host": "127.0.0.1",
        "mqtt_port": 1883,
        "clock_method": "gateway canonical sample sequence for event lineage; local perf_counter_ns for adapter runtime only; no physical acquisition-to-ACK latency claim",
        "event_id_rule": "bridge-{scenario}-{source}-{record}-p{detected_peak_sample:05d}",
        "trace_columns": ["scenario", "source", "record", "source_files_sha256", "event_id", "endpoint_sample_start", "endpoint_sample_stop_exclusive", "detected_peak_sample", "peak_emission_sample", "window_eligible", "model_probability", "signal_quality", "decision_threshold", "requested_action", "ack_status", "terminal_status", "reason_code", "audit_identifier"],
        "offline_peak_match_tolerance_ms": 150,
        "channel_1_diagnostic": {"records": ["mitdb:100", "incartdb:I01"], "clean_and_dropout_runs": True, "channel_index": 0, "replacement": 0.0, "start_sample_in_fragment": DROP_START, "stop_sample_exclusive_in_fragment": DROP_STOP, "unchanged_channel_index": 1},
        "acceptance": {"all_eligible_events_have_peak_action_terminal_ack_lineage": True, "accepted_audit_completeness": 1.0, "rejected_reason_completeness": 1.0, "frozen_hashes_match": True, "no_unresolved_transport_callback_error": True, "offline_peak_locations_match_within_registered_tolerance": True},
        "claim_boundary": "No new clinical F1, physical acquisition, hardware latency, or change to Gate S2/Gate V. Missing no-event reacquire ACK in channel dropout must be reported as a limitation.",
    }
    write_json_once(output / "protocol.json", protocol)


class BridgeRun:
    def __init__(self, scenario: str, row: dict, samples: np.ndarray, output: Path, host: str, port: int) -> None:
        self.scenario, self.row, self.samples = scenario, row, samples
        self.key = f"{row['source']}:{row['record']}"
        self.endpoint_id = f"endpoint-{scenario}-{row['source']}-{row['record']}"
        self.transport = LocalMqttV5Transport(host, port)
        self.store = GatewayStore(output / f"audit_{scenario}_{row['source']}_{row['record']}.sqlite")
        self.policy = PolicyV1()
        self.inference = FrozenInt8Inference(MANIFEST)
        self.ingest = GatewayIngest("gateway-sim", MODEL_SHA256, self.policy.version, self.store, self.policy)
        self.prefix = np.empty((0, 2), dtype=np.float32)
        self.raw_next_sequence = 0
        self.event_next_sequence = 0
        self.emitted_peak_samples: set[int] = set()
        self.online_peaks = []
        self.traces: list[dict] = []
        self.errors: list[str] = []
        self.raw_packet_count = 0
        self.detector_call_count = 0
        self.detector_runtime_ms = 0.0
        self.raw_done: dict[int, threading.Event] = {}
        self.ack_events: dict[str, threading.Event] = {}
        self.acks: dict[str, dict] = {}
        self.transport.subscribe(f"ecg/{self.endpoint_id}/samples", self.on_raw_packet)
        self.transport.subscribe(f"ecg/{self.endpoint_id}/ack", self.on_ack)

    def on_ack(self, payload: dict) -> None:
        self.acks[payload["event_id"]] = payload
        signal = self.ack_events.get(payload["event_id"])
        if signal is not None:
            signal.set()

    def on_raw_packet(self, payload: dict) -> None:
        sequence = int(payload["sample_sequence"])
        try:
            if sequence != self.raw_next_sequence:
                raise ValueError(f"raw_sequence_mismatch:{sequence}:{self.raw_next_sequence}")
            chunk = np.asarray(payload["samples"], dtype=np.float32)
            if chunk.ndim != 2 or chunk.shape[1] != 2 or not np.isfinite(chunk).all():
                raise ValueError("malformed_raw_chunk")
            self.prefix = np.concatenate((self.prefix, chunk), axis=0)
            self.raw_next_sequence += len(chunk)
            self.raw_packet_count += 1
            if len(self.prefix) < 720:
                return
            started = time.perf_counter_ns()
            peaks = detector.causal_pan_tompkins(self.prefix[:, 0], SAMPLE_RATE)
            self.detector_runtime_ms += (time.perf_counter_ns() - started) / 1e6
            self.detector_call_count += 1
            for peak in peaks:
                if peak.peak_sample in self.emitted_peak_samples:
                    continue
                if peak.peak_sample < HALF_WINDOW or peak.peak_sample + HALF_WINDOW > len(self.prefix):
                    continue
                self.emit_event(peak, peaks)
        except Exception as error:
            self.errors.append(f"{type(error).__name__}:{error}")
        finally:
            signal = self.raw_done.get(sequence)
            if signal is not None:
                signal.set()

    def emit_event(self, peak, peaks) -> None:
        stop = max(peak.peak_sample + HALF_WINDOW, peak.emitted_sample + 1, self.event_next_sequence + 1)
        if stop > len(self.prefix):
            raise ValueError("event_not_yet_available")
        start = self.event_next_sequence
        window = normalise_window(self.prefix[peak.peak_sample - HALF_WINDOW:peak.peak_sample + HALF_WINDOW])
        history = np.asarray([item.peak_sample for item in peaks], dtype=np.int64)
        rr = experiment5.rr_features(np.asarray([peak.peak_sample], dtype=np.int64), history)[0]
        amplitude = np.ptp(window[:, 0])
        noise = np.median(np.abs(np.diff(window[:, 0]))) + 1e-6
        quality = float(np.clip(amplitude / (20 * noise), 0.0, 1.0))
        event_id = f"bridge-{self.scenario}-{self.row['source']}-{self.row['record']}-p{peak.peak_sample:05d}"
        packet = ECGPacket(event_id, self.endpoint_id, "gateway-sim", start, utc_now(), "two_channel", SAMPLE_RATE, "local_mqtt_v5_qos1", MODEL_SHA256, "policy-v1", self.prefix[start:stop].tolist())
        inference: dict = {}

        def event_factory(accepted_packet: ECGPacket) -> GatewayEvent:
            probability, metadata = self.inference.infer(window, rr, quality)
            inference["probability"] = probability
            return GatewayEvent(accepted_packet.event_id, accepted_packet.endpoint_id, accepted_packet.gateway_id, accepted_packet.sample_sequence, accepted_packet.recorded_at, accepted_packet.lead_profile, accepted_packet.native_sample_rate_hz, accepted_packet.transport_profile, metadata["model_sha256"], accepted_packet.policy_version, quality, probability, metadata["decision_threshold"])

        ack = self.ingest.accept(packet.to_dict(), event_factory)
        self.store.queue_ack(event_id, f"ecg/{self.endpoint_id}/ack", ack.to_dict())
        self.ack_events[event_id] = threading.Event()
        self.transport.publish(f"ecg/{self.endpoint_id}/ack", ack.to_dict())
        self.store.mark_delivered(event_id)
        self.event_next_sequence = stop if ack.ack_status == "accepted" else start
        self.emitted_peak_samples.add(peak.peak_sample)
        self.online_peaks.append(peak)
        self.traces.append({"scenario": self.scenario, "source": self.row["source"], "record": self.row["record"], "source_files_sha256": json.dumps(self.row["source_files_sha256"], sort_keys=True), "event_id": event_id, "endpoint_sample_start": start, "endpoint_sample_stop_exclusive": stop, "detected_peak_sample": peak.peak_sample, "peak_emission_sample": peak.emitted_sample, "window_eligible": True, "model_probability": inference.get("probability"), "signal_quality": quality, "decision_threshold": 0.49, "requested_action": ack.requested_action, "ack_status": None, "terminal_status": None, "reason_code": ack.reason, "audit_identifier": event_id})

    def run(self) -> dict:
        try:
            for start in range(0, len(self.samples), CHUNK_SAMPLES):
                chunk = self.samples[start:start + CHUNK_SAMPLES]
                self.raw_done[start] = threading.Event()
                self.transport.publish(f"ecg/{self.endpoint_id}/samples", {"sample_sequence": start, "samples": chunk.tolist(), "source": self.row["source"], "record": self.row["record"], "recorded_at": utc_now(), "simulated_acquisition_endpoint": True})
                if not self.raw_done[start].wait(20.0):
                    self.errors.append(f"raw_callback_timeout:{start}")
                    break
                if self.errors:
                    break
            for event_id, signal in self.ack_events.items():
                if not signal.wait(10.0):
                    self.errors.append(f"event_ack_timeout:{event_id}")
            for trace in self.traces:
                ack = self.acks.get(trace["event_id"], {})
                trace["ack_status"] = ack.get("ack_status", "missing")
                trace["terminal_status"] = ack.get("terminal_status", "missing")
                trace["requested_action"] = ack.get("requested_action", trace["requested_action"])
                trace["reason_code"] = ack.get("reason", trace["reason_code"])
            offline = detector.causal_pan_tompkins(self.samples[:, 0], SAMPLE_RATE)
            eligible_offline = [peak for peak in offline if peak.peak_sample >= HALF_WINDOW and peak.peak_sample + HALF_WINDOW <= len(self.samples)]
            matches, missed, unmatched = detector.match_peaks([(item.peak_sample, "peak") for item in eligible_offline], self.online_peaks, MATCH_TOLERANCE_SAMPLES)
            audit = self.store.accepted_audit_completeness()
            rejected_audit = self.store.rejected_reason_completeness()
            actions = {name: sum(trace["requested_action"] == name for trace in self.traces) for name in ("monitor", "reacquire", "buffer_segment", "request_review", "reject")}
            gap_events = [trace for trace in self.traces if DROP_START <= trace["detected_peak_sample"] < DROP_STOP]
            return {"scenario": self.scenario, "record_key": self.key, "raw_packets_sent": (len(self.samples) + CHUNK_SAMPLES - 1) // CHUNK_SAMPLES, "raw_packets_received": self.raw_packet_count, "raw_samples_received": self.raw_next_sequence, "detected_peaks_offline": len(offline), "eligible_windows_offline": len(eligible_offline), "eligible_events_online": len(self.traces), "window_formation_rate": len(self.traces) / len(eligible_offline) if eligible_offline else None, "peak_matches_within_150ms": len(matches), "peak_missed": len(missed), "peak_unmatched": len(unmatched), "accepted_events": self.store.accepted_count(), "rejected_events": self.store.rejected_count(), "acknowledged_events": sum(trace["ack_status"] != "missing" for trace in self.traces), "missing_acknowledgements": sum(trace["ack_status"] == "missing" for trace in self.traces), "actions": actions, "accepted_audit": audit, "rejected_reason_audit": rejected_audit, "detector_prefix_calls": self.detector_call_count, "detector_repeated_prefix_runtime_ms": self.detector_runtime_ms, "drop_interval_events": len(gap_events), "drop_interval_reacquire_acks": sum(trace["ack_status"] == "accepted" and trace["requested_action"] == "reacquire" for trace in gap_events), "errors": self.errors + self.transport.callback_errors}
        finally:
            self.transport.close()
            self.store.close()


def run(data_root: Path, output: Path, host: str, port: int) -> None:
    protocol_path = output / "protocol.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    _, original = frozen_inputs()
    if protocol["source_replay_protocol_sha256"] != sha256(SOURCE_PROTOCOL) or protocol["manifest_sha256"] != sha256(MANIFEST):
        raise ValueError("registered_protocol_hash_mismatch")
    for name, registered_hash in protocol["source_code_sha256"].items():
        if sha256(ROOT / name) != registered_hash:
            raise ValueError(f"source_changed_after_registration:{name}")
    if protocol["fragments"] != original["fragments"]:
        raise ValueError("registered_fragment_mismatch")
    if (output / "summary.json").exists():
        raise FileExistsError("bridge summary already exists")
    summaries, traces = [], []
    for row in protocol["fragments"]:
        samples, metadata = real_replay.fixed_fragment(data_root, row["source"], row["record"])
        if metadata != row:
            raise ValueError(f"source_fragment_hash_mismatch:{row['source']}:{row['record']}")
        cases = ["baseline"]
        if f"{row['source']}:{row['record']}" in protocol["channel_1_diagnostic"]["records"]:
            cases.append("channel1_dropout")
        for case in cases:
            prepared = samples.copy()
            if case == "channel1_dropout":
                prepared[DROP_START:DROP_STOP, 0] = 0.0
            bridge = BridgeRun(case, row, prepared, output, host, port)
            summary = bridge.run()
            summaries.append(summary)
            traces.extend(bridge.traces)
            if summary["errors"]:
                break
        if summaries[-1]["errors"]:
            break
    with (output / "events.csv").open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=protocol["trace_columns"])
        writer.writeheader()
        writer.writerows(traces)
    with (output / "per_fragment.json").open("x", encoding="utf-8") as handle:
        json.dump(summaries, handle, indent=2)
        handle.write("\n")
    baseline = [item for item in summaries if item["scenario"] == "baseline"]
    diagnostic = [item for item in summaries if item["scenario"] == "channel1_dropout"]
    acceptance = {
        "all_ten_baselines_completed": len(baseline) == 10,
        "all_eligible_events_have_peak_action_terminal_ack_lineage": all(trace["ack_status"] == "accepted" and trace["terminal_status"] == "completed" and trace["audit_identifier"] for trace in traces),
        "accepted_audit_complete": all(item["accepted_audit"]["completeness"] == 1.0 for item in summaries),
        "rejected_reason_complete": all(item["rejected_reason_audit"]["completeness"] == 1.0 for item in summaries),
        "offline_peak_locations_match": all(item["peak_missed"] == 0 and item["peak_unmatched"] == 0 for item in summaries),
        "no_unresolved_transport_error": all(not item["errors"] for item in summaries),
        "frozen_configuration_hashes_match": True,
    }
    report = {"experiment": protocol["experiment"], "status": "completed" if all(acceptance.values()) else "completed_with_unmet_criteria", "evidence_class": protocol["evidence_class"], "baselines": len(baseline), "channel1_diagnostics": len(diagnostic), "raw_packets_received": sum(item["raw_packets_received"] for item in summaries), "eligible_events": sum(item["eligible_events_online"] for item in summaries), "acknowledged_events": sum(item["acknowledged_events"] for item in summaries), "accepted_events": sum(item["accepted_events"] for item in summaries), "acceptance": acceptance, "channel1_loss_observation": [{"record_key": item["record_key"], "drop_interval_events": item["drop_interval_events"], "drop_interval_reacquire_acks": item["drop_interval_reacquire_acks"], "no_event_reacquire_fallback_verified": item["drop_interval_reacquire_acks"] > 0} for item in diagnostic], "claim_boundary": protocol["claim_boundary"], "protocol_sha256": sha256(protocol_path)}
    write_json_once(output / "summary.json", report)
    print(json.dumps(report, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("register", "run"))
    parser.add_argument("--data-root", type=Path, default=ROOT / "data")
    parser.add_argument("--output", type=Path, default=RESULT)
    parser.add_argument("--mqtt-host", default="127.0.0.1")
    parser.add_argument("--mqtt-port", type=int, default=1883)
    args = parser.parse_args()
    if args.mode == "register":
        register(args.data_root, args.output)
    else:
        run(args.data_root, args.output, args.mqtt_host, args.mqtt_port)


if __name__ == "__main__":
    main()
