"""Merge immutable Experiment 6 Part 2 condition shards."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


ROOT = Path(__file__).parents[1]
SHARDS = [ROOT / "results/experiment6_part2_a", ROOT / "results/experiment6_part2_b"]
OUTPUT = ROOT / "results/experiment6_part2"
EXPECTED_CONDITIONS = {
    "amplitude_0p5",
    "amplitude_1p0",
    "amplitude_2p0",
    "sample_loss_50",
    "timing_jitter_5ms",
    "lead_dropout_ch1",
    "lead_dropout_ch2",
}
EXPECTED_RECORDS = 219


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    if OUTPUT.exists():
        raise FileExistsError(f"Refusing to overwrite {OUTPUT}")
    summaries = [json.loads((shard / "summary.json").read_text(encoding="utf-8")) for shard in SHARDS]
    protocols = [json.loads((shard / "protocol.json").read_text(encoding="utf-8")) for shard in SHARDS]
    conditions = [condition for summary in summaries for condition in summary["conditions"].values()]
    names = {condition["condition"]["name"] for condition in conditions}
    if names != EXPECTED_CONDITIONS or len(conditions) != len(EXPECTED_CONDITIONS):
        raise ValueError(f"Condition coverage mismatch: {sorted(names)}")
    if any(summary["record_count_per_condition"] != EXPECTED_RECORDS for summary in summaries):
        raise ValueError("A shard does not contain 219 records per condition")
    model_hashes = {protocol["model_sha256"] for protocol in protocols}
    calibration_hashes = {protocol["calibration_sha256"] for protocol in protocols}
    manifest_hashes = {protocol["freeze_manifest_sha256"] for protocol in protocols}
    if len(model_hashes) != 1 or len(calibration_hashes) != 1 or len(manifest_hashes) != 1:
        raise ValueError("Frozen artifact hashes differ across shards")

    OUTPUT.mkdir(parents=True)
    ordered_conditions = sorted(conditions, key=lambda item: item["condition"]["name"])
    protocol = {
        "experiment": "experiment_6_signal_robustness_part2",
        "status": "complete",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "parent_experiment": "experiment_6_signal_robustness",
        "part_definition": "amplitude scaling, 50-sample loss, 5 ms timing jitter, and single-channel lead dropout",
        "model_sha256": next(iter(model_hashes)),
        "calibration_sha256": next(iter(calibration_hashes)),
        "freeze_manifest_sha256": next(iter(manifest_hashes)),
        "threshold": protocols[0]["threshold"],
        "conditions": [condition["condition"] for condition in ordered_conditions],
        "records_per_condition": EXPECTED_RECORDS,
        "prohibited_operations": protocols[0]["prohibited_operations"],
        "shards": [str(shard) for shard in SHARDS],
        "write_once": True,
    }
    (OUTPUT / "protocol.json").write_text(json.dumps(protocol, indent=2) + "\n", encoding="utf-8")
    (OUTPUT / "perturbation_manifest.json").write_text(json.dumps({"conditions": protocol["conditions"], "records_per_condition": EXPECTED_RECORDS, "source_shards": [str(shard / "perturbation_manifest.json") for shard in SHARDS]}, indent=2) + "\n", encoding="utf-8")

    rows = []
    for shard in SHARDS:
        with (shard / "per_record_metrics.csv").open(newline="", encoding="utf-8") as handle:
            rows.extend(csv.DictReader(handle))
    with (OUTPUT / "per_record_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = sorted({field for row in rows for field in row})
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    arrays = {}
    for shard in SHARDS:
        with np.load(shard / "per_record_predictions.npz") as archive:
            arrays.update({key: archive[key] for key in archive.files})
    np.savez_compressed(OUTPUT / "per_record_predictions.npz", **arrays)

    summary = {
        "experiment": "experiment_6_signal_robustness_part2",
        "status": "complete",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "frozen_configuration_verified": True,
        "condition_count": len(EXPECTED_CONDITIONS),
        "record_count_per_condition": EXPECTED_RECORDS,
        "conditions": {condition["condition"]["name"]: condition for condition in ordered_conditions},
        "artifacts": {"protocol": str(OUTPUT / "protocol.json"), "perturbation_manifest": str(OUTPUT / "perturbation_manifest.json"), "per_record_metrics": str(OUTPUT / "per_record_metrics.csv"), "per_record_predictions": str(OUTPUT / "per_record_predictions.npz")},
        "source_shards": [str(shard / "summary.json") for shard in SHARDS],
        "post_evaluation_rule": "Part 2 results are descriptive robustness evidence; no model, detector, calibration, threshold, quantization, preprocessing, lead profile, or seed change may be selected.",
    }
    (OUTPUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    integrity = {
        "status": "verified",
        "model_sha256": protocol["model_sha256"],
        "calibration_sha256": protocol["calibration_sha256"],
        "freeze_manifest_sha256": protocol["freeze_manifest_sha256"],
        "artifact_sha256": {name: sha256(OUTPUT / name) for name in ("protocol.json", "perturbation_manifest.json", "per_record_metrics.csv", "per_record_predictions.npz", "summary.json")},
        "row_count": len(rows),
        "array_count": len(arrays),
    }
    (OUTPUT / "integrity_verification.json").write_text(json.dumps(integrity, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "complete", "conditions": len(EXPECTED_CONDITIONS), "records_per_condition": EXPECTED_RECORDS, "rows": len(rows), "arrays": len(arrays)}, indent=2))


if __name__ == "__main__":
    main()
