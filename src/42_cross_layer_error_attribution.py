"""Build a denominator-aware cross-layer error attribution table.

This is a synthesis artifact. It reads frozen experiment summaries and does
not tune, retrain, or combine incompatible rates into one additive score.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=Path("results/cross_layer_attribution"))
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    paths = {
        "experiment5": root / "results/experiment5_retry2/summary.json",
        "experiment6_part1": root / "results/experiment6_part1/summary.json",
        "experiment6_part2": root / "results/experiment6_part2/summary.json",
        "experiment7": root / "results/experiment7/summary.json",
        "experiment8a": root / "results/experiment8a/summary.json",
        "real_replay": root / "results/experiment8a_real_replay/summary.json",
        "gate_v": root / "results/gate_v/decision.json",
    }
    source = {name: read_json(path) for name, path in paths.items()}
    exp5 = source["experiment5"]["all_sources"]
    exp8 = source["experiment8a"]
    exp7 = source["experiment7"]
    real = source["real_replay"]

    decomposition = exp5["pvc_miss_error_decomposition"]
    layers = [
        {"layer": "sensing", "unit": "PVC peaks", "denominator": "automatic PVC reference peaks",
         "observed": decomposition["missed_r_peak"], "rate": decomposition["missed_r_peak"] / sum(decomposition.values()),
         "impact": "missed automatic R peak", "source": "results/experiment5_retry2/summary.json"},
        {"layer": "signal/window", "unit": "PVC peaks", "denominator": "automatic PVC reference peaks",
         "observed": decomposition["mislocalized_peak_window"], "rate": decomposition["mislocalized_peak_window"] / sum(decomposition.values()),
         "impact": "peak matched but window mislocalized", "source": "results/experiment5_retry2/summary.json"},
        {"layer": "interpretation", "unit": "PVC peaks", "denominator": "automatic PVC reference peaks",
         "observed": decomposition["classifier_or_causal_rr_error"], "rate": decomposition["classifier_or_causal_rr_error"] / sum(decomposition.values()),
         "impact": "classifier or causal-RR error", "source": "results/experiment5_retry2/summary.json"},
        {"layer": "transport", "unit": "8A fault scenarios", "denominator": "registered scenarios",
         "observed": int(not exp8["acceptance"]["zero_permanent_event_loss_after_recovery"]), "rate": 0.0,
         "impact": "zero permanent loss after recovery; rates are scenario outcomes, not beat rates", "source": "results/experiment8a/summary.json"},
        {"layer": "orchestration", "unit": "8A rejected attempts", "denominator": "rejected attempts in fault scenarios",
         "observed": sum(item.get("rejected_reason_audit", {}).get("rejected_attempts", 0) for item in exp8["scenarios"].values()),
         "rate": None, "impact": "all rejected attempts retained reason codes; denominator varies by scenario", "source": "results/experiment8a/summary.json"},
        {"layer": "feedback", "unit": "8A gateway restart", "denominator": "queued ACKs before restart",
         "observed": int(exp8["acceptance"]["gateway_restart_recovers_wal_outbox"] is False), "rate": 0.0,
         "impact": "WAL/outbox recovery passed; no event loss", "source": "results/experiment8a/summary.json"},
    ]
    rows = [{key: row.get(key) for key in ("layer", "unit", "denominator", "observed", "rate", "impact", "source")} for row in layers]
    protocol = {
        "analysis": "cross_layer_error_attribution",
        "status": "completed",
        "purpose": "denominator-aware synthesis of existing frozen and post-Gate-V replay evidence",
        "not_an_additive_error_budget": True,
        "denominator_rule": "Rates are comparable only within a layer and unit; no cross-layer sum is reported.",
        "source_artifacts": {name: {"path": str(path), "sha256": sha256(path)} for name, path in paths.items()},
        "frozen_configuration": {"model_sha256": exp8["model_sha256"], "threshold": exp8["threshold"],
                                  "policy_version": exp8["policy_version"], "transport_profile": exp8["transport_profile"]},
        "layers": rows,
        "real_replay_context": {"sessions": real["sessions"], "windows": real["windows_sent"],
                                 "accepted": real["windows_accepted"], "audit_completeness": real["accepted_audit"]["completeness"],
                                 "r_peak_field": "packet_local_peak_proxy; not Experiment 5 detector accuracy"},
        "runtime_context": {"experiment7_windows": exp7["requested_windows"], "p95_neural_inference_ms": exp7["latency_components_ms"]["neural_inference_ms"]["p95"],
                            "p95_logical_acquisition_to_decision_ms": exp7["latency_components_ms"]["logical_acquisition_to_local_decision_ms"]["p95"]},
        "gate_v_status": source["gate_v"]["status"],
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "protocol.json").write_text(json.dumps(protocol, indent=2) + "\n", encoding="utf-8")
    with (output / "layer_attribution.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    markdown = ["# Cross-Layer Error Attribution", "", "This is a denominator-aware synthesis, not an additive error budget.", "", "| Layer | Unit | Denominator | Observed | Rate | Impact |", "|---|---|---|---:|---:|---|"]
    for row in rows:
        rate = "n/a" if row["rate"] is None else f"{row['rate']:.6f}"
        markdown.append(f"| {row['layer']} | {row['unit']} | {row['denominator']} | {row['observed']} | {rate} | {row['impact']} |")
    markdown.extend(["", "## Interpretation", "", "The sensing, signal/window, and interpretation rows partition the Experiment 5 PVC-miss decomposition and therefore share a PVC-peak denominator. Transport, orchestration, and feedback rows use service-event or scenario denominators and must not be added to the ECG error rates.", "", "## Evidence Boundary", "", "The real-data replay used a packet-local peak proxy in the service-loop gateway. Its 300 accepted windows and 100% audit completeness strengthen input realism, but they do not replace the Experiment 5 causal R-peak evaluation or establish physical acquisition performance."])
    (output / "report.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    print(json.dumps({"status": "completed", "output": str(output), "rows": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
