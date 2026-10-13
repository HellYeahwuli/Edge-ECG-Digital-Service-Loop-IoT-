"""Evaluate Gate V from completed Experiment 8A and Experiment 7 artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment8a", type=Path, default=Path("results/experiment8a/summary.json"))
    parser.add_argument("--experiment7", type=Path, default=Path("results/experiment7/summary.json"))
    parser.add_argument("--output", type=Path, default=Path("results/gate_v/decision.json"))
    args = parser.parse_args()
    eight = json.loads(args.experiment8a.read_text(encoding="utf-8"))
    seven = json.loads(args.experiment7.read_text(encoding="utf-8"))
    eight_acceptance = eight.get("acceptance", {})
    seven_targets = seven.get("targets", {})
    restart = eight.get("scenarios", {}).get("gateway_restart", {})
    saturation = eight.get("scenarios", {}).get("buffer_saturation", {})
    criteria = {
        "experiment8a_completed": eight.get("status") == "completed",
        "experiment7_completed": seven.get("status") == "completed",
        "primary_transport_is_local_mqtt_v5_qos1": eight.get("transport_profile") == "local_mqtt_v5_qos1",
        "same_transport_profile": eight.get("transport_profile") == seven.get("transport_profile"),
        "same_model_sha256": eight.get("model_sha256") == seven.get("model_sha256"),
        "same_threshold": eight.get("threshold") == seven.get("threshold"),
        "same_policy_version": eight.get("policy_version") == seven.get("policy_version") == "policy-v1",
        "same_service_contract_version": eight.get("service_contract_version") == seven.get("service_contract_version"),
        "zero_duplicate_actions": eight_acceptance.get("zero_duplicate_actions") is True,
        "zero_permanent_event_loss_after_recovery": eight_acceptance.get("zero_permanent_event_loss_after_recovery") is True,
        "accepted_audit_completeness_100pct": eight_acceptance.get("accepted_audit_completeness_100pct") is True and seven_targets.get("accepted_audit_completeness_100pct") is True,
        "rejected_reason_completeness_100pct": eight_acceptance.get("rejected_reason_completeness_100pct") is True,
        "gateway_restart_recovers_wal_outbox": restart.get("pending_before_restart", 0) > 0 and restart.get("recovery", {}).get("delivered", 0) > 0 and restart.get("next_event_after_restart", {}).get("ack", {}).get("ack_status") == "accepted",
        "bounded_buffer_saturation_is_explicit": saturation.get("buffer_overflow_count", 0) > 0,
        "local_loop_survives_internet_outage": eight_acceptance.get("local_loop_survives_internet_outage") is True,
        "no_transport_callback_errors": eight_acceptance.get("no_transport_callback_errors") is True and seven_targets.get("no_transport_callback_errors") is True,
        "runtime_model_size_target": seven_targets.get("int8_model_under_1_mib") is True,
        "runtime_inference_latency_target": seven_targets.get("p95_neural_inference_under_50_ms") is True,
        "runtime_local_decision_latency_target": seven_targets.get("p95_acquisition_to_local_decision_under_600_ms") is True,
        "runtime_sample_size_target": seven_targets.get("at_least_1000_inference_windows") is True and seven_targets.get("at_least_30_sessions") is True,
        "software_only_evidence_labels": "software-only" in str(eight.get("evidence_class", "")) and "software runtime" in str(seven.get("evidence_class", "")),
        "frozen_model_unchanged": eight.get("model_or_threshold_changed") is False and seven.get("model_or_threshold_changed") is False,
        "no_external_data_access": eight.get("external_data_accessed") is False and seven.get("external_data_accessed") is False,
    }
    passed = all(criteria.values())
    decision = {
        "gate": "Gate V: Software Loop Validation",
        "status": "passed" if passed else "failed",
        "evidence_class": "software-simulated two-tier local-edge service loop",
        "criteria": criteria,
        "source_artifacts": {
            "experiment8a_summary": str(args.experiment8a.resolve()),
            "experiment8a_summary_sha256": sha256(args.experiment8a),
            "experiment7_summary": str(args.experiment7.resolve()),
            "experiment7_summary_sha256": sha256(args.experiment7),
        },
        "claim_boundary": "Gate V does not establish physical ECG acquisition, hardware latency, energy consumption, MCU or wearable suitability, clinical efficacy, regulatory approval, or a physical deployment.",
        "model_or_threshold_changed": False,
        "external_data_accessed": False,
    }
    write_json(args.output, decision)
    print(json.dumps(decision, indent=2, ensure_ascii=False))
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
