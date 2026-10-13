"""Run the frozen Experiment 6 signal-robustness evaluation.

The Gate S2 P0/O1 M1/L2 int8 artifact, Platt map, threshold, lead mapping,
and causal detector are immutable. Synthetic perturbations are registered in
the protocol and are evaluated without fitting or selection.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import platform
import sys
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import wfdb
from scipy.signal import butter, sosfilt

from multisource_ecg import SOURCE_BY_KEY, TARGET_SAMPLE_RATE_HZ, load_pvc_windows, normalise_window, resample_channels, select_leads


MODEL_SHA256 = "edea13aacdd5f6f9f94a3b73092f567f25b4dcade6133da4af7eb42aa2913776"
CALIBRATION_SHA256 = "1525a1988a25021e3398a0cee5bef66263c30d31d24c159cdb730a94dcba59fa"
MANIFEST_SHA256 = "6a091daa2f32fbb45b33772ef8fda7029988741cf57adb18b4e5b3f336f1c6bd"
THRESHOLD = 0.49
TOLERANCE_SAMPLES = int(round(150 * TARGET_SAMPLE_RATE_HZ / 1000))
HALF_WINDOW = 150
BOOTSTRAP_SEED = 20260803
BOOTSTRAP_RESAMPLES = 2000
BASE_SEED = 20260806
EXPECTED = {"mitdb": 48, "incartdb": 75, "svdb": 78, "nsrdb": 18}
ROLES = {"mitdb": "training_development", "incartdb": "training_development", "svdb": "locked_external_test", "nsrdb": "normal_rhythm_evaluation_only"}


def load_module(filename: str, name: str):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


experiment3 = load_module("32_experiment3_frozen_svdb.py", "experiment6_experiment3")
detector = load_module("06_evaluate_streaming_rpeaks.py", "experiment6_detector")
base, core = experiment3.base, experiment3.core


CONDITIONS = [
    {"name": "clean", "kind": "clean"},
    {"name": "baseline_wander", "kind": "baseline_wander", "frequency_hz": 0.5, "amplitude_rms_ratio": 0.20},
    {"name": "interference_50hz", "kind": "interference", "frequency_hz": 50.0, "amplitude_rms_ratio": 0.10},
    {"name": "interference_60hz", "kind": "interference", "frequency_hz": 60.0, "amplitude_rms_ratio": 0.10},
    {"name": "muscle_noise_20db", "kind": "muscle_noise", "snr_db": 20.0, "low_hz": 20.0, "high_hz": 100.0},
    {"name": "muscle_noise_10db", "kind": "muscle_noise", "snr_db": 10.0, "low_hz": 20.0, "high_hz": 100.0},
    {"name": "muscle_noise_5db", "kind": "muscle_noise", "snr_db": 5.0, "low_hz": 20.0, "high_hz": 100.0},
    {"name": "amplitude_0p5", "kind": "amplitude", "scale": 0.5},
    {"name": "amplitude_1p0", "kind": "amplitude", "scale": 1.0},
    {"name": "amplitude_2p0", "kind": "amplitude", "scale": 2.0},
    {"name": "sample_loss_50", "kind": "sample_loss", "loss_samples": 50},
    {"name": "timing_jitter_5ms", "kind": "timing_jitter", "jitter_ms": 5.0},
    {"name": "lead_dropout_ch1", "kind": "lead_dropout", "channel": 0},
    {"name": "lead_dropout_ch2", "kind": "lead_dropout", "channel": 1},
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: dict) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite Experiment 6 artifact: {path}")
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def records_from_manifest(path: Path) -> list[dict]:
    records = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["source"] in EXPECTED:
                if row["role"] != ROLES[row["source"]]:
                    raise ValueError(f"Role mismatch for {row['source']}:{row['record']}")
                records.append(row)
    for source, expected in EXPECTED.items():
        actual = sum(row["source"] == source for row in records)
        if actual != expected:
            raise ValueError(f"Expected {expected} {source} records, found {actual}")
    return sorted(records, key=lambda row: (row["source"], row["record"]))


def rr_features(peaks: np.ndarray, history_peaks: np.ndarray) -> np.ndarray:
    output = []
    for peak in peaks:
        index = int(np.searchsorted(history_peaks, peak, side="left"))
        preceding = history_peaks[:index]
        if len(preceding):
            pre = float(peak - preceding[-1]) / TARGET_SAMPLE_RATE_HZ
            previous = np.diff(preceding[-2:]) / TARGET_SAMPLE_RATE_HZ
            prev = float(previous[-1]) if len(previous) else pre
            history = np.diff(preceding[-9:]) / TARGET_SAMPLE_RATE_HZ
            median = float(np.median(history)) if len(history) else pre
            valid_pre, valid_history = 1.0, float(len(history) >= 8)
        else:
            pre, prev, median, valid_pre, valid_history = 1.0, 1.0, 1.0, 0.0, 0.0
        pre = float(np.clip(pre, 0.2, 3.0))
        output.append([pre, pre / max(median, 0.2), pre / max(prev, 0.2), valid_pre, valid_history])
    return np.asarray(output, dtype=np.float32)


def binary(labels: np.ndarray, predictions: np.ndarray) -> dict:
    tn = int(np.sum((labels == 0) & (predictions == 0)))
    fp = int(np.sum((labels == 0) & (predictions == 1)))
    fn = int(np.sum((labels == 1) & (predictions == 0)))
    tp = int(np.sum((labels == 1) & (predictions == 1)))
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    specificity = tn / max(tn + fp, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-12)
    return {"tn": tn, "fp": fp, "fn": fn, "tp": tp, "pvc_precision": precision, "pvc_recall": recall, "pvc_f1": f1, "specificity": specificity}


def perturb(signal: np.ndarray, condition: dict, rng: np.random.Generator) -> np.ndarray:
    result = signal.astype(np.float32, copy=True)
    n, channels = result.shape
    t = np.arange(n, dtype=np.float32) / TARGET_SAMPLE_RATE_HZ
    kind = condition["kind"]
    if kind == "clean":
        return result
    if kind == "baseline_wander":
        rms = np.sqrt(np.mean(result ** 2, axis=0, keepdims=True))
        result += (condition["amplitude_rms_ratio"] * rms * np.sin(2 * np.pi * condition["frequency_hz"] * t)[:, None]).astype(np.float32)
    elif kind == "interference":
        rms = np.sqrt(np.mean(result ** 2, axis=0, keepdims=True))
        phase = rng.uniform(0, 2 * np.pi, size=(1, channels))
        result += (condition["amplitude_rms_ratio"] * rms * np.sin(2 * np.pi * condition["frequency_hz"] * t[:, None] + phase)).astype(np.float32)
    elif kind == "muscle_noise":
        sos = butter(4, [condition["low_hz"], condition["high_hz"]], btype="bandpass", fs=TARGET_SAMPLE_RATE_HZ, output="sos")
        noise = sosfilt(sos, rng.normal(size=(n, channels)).astype(np.float64), axis=0).astype(np.float32)
        signal_rms = np.sqrt(np.mean(result ** 2, axis=0, keepdims=True))
        noise_rms = np.sqrt(np.mean(noise ** 2, axis=0, keepdims=True))
        target_noise_rms = signal_rms / (10 ** (condition["snr_db"] / 20.0))
        result += noise * (target_noise_rms / np.maximum(noise_rms, 1e-8))
    elif kind == "amplitude":
        result *= float(condition["scale"])
    elif kind == "sample_loss":
        length = int(condition["loss_samples"])
        start = int(rng.integers(HALF_WINDOW, max(HALF_WINDOW + 1, n - HALF_WINDOW - length)))
        result[start:start + length, :] = 0.0
    elif kind == "timing_jitter":
        jitter = rng.uniform(-condition["jitter_ms"] / 1000.0, condition["jitter_ms"] / 1000.0, size=n).astype(np.float32)
        source_positions = np.clip(np.arange(n, dtype=np.float32) + jitter * TARGET_SAMPLE_RATE_HZ, 0, n - 1)
        base_positions = np.arange(n, dtype=np.float32)
        for channel in range(channels):
            result[:, channel] = np.interp(base_positions, source_positions, result[:, channel]).astype(np.float32)
    elif kind == "lead_dropout":
        result[:, int(condition["channel"])] = 0.0
    else:
        raise ValueError(f"Unknown perturbation kind: {kind}")
    return result


def count_policy_escalations(samples: np.ndarray, probabilities: np.ndarray, duration_seconds: float) -> dict:
    high_risk = deque()
    counts = Counter({"monitor": 0, "buffer_segment": 0, "request_review": 0})
    for sample, probability in zip(samples, probabilities):
        if probability < THRESHOLD:
            counts["monitor"] += 1
            continue
        timestamp = float(sample) / TARGET_SAMPLE_RATE_HZ
        high_risk.append(timestamp)
        while high_risk and timestamp - high_risk[0] > 30.0:
            high_risk.popleft()
        if len(high_risk) >= 3:
            counts["request_review"] += 1
        else:
            counts["buffer_segment"] += 1
    hours = duration_seconds / 3600.0
    return {**{key: int(value) for key, value in counts.items()}, "false_service_escalations_per_hour": counts["request_review"] / max(hours, 1e-12)}


def evaluate_record(row: dict, data_root: Path, model: Path, scaler, condition: dict, seed: int) -> tuple[dict, dict]:
    source, record = row["source"], row["record"]
    spec = SOURCE_BY_KEY[source]
    record_base = data_root / spec.directory / record
    header = wfdb.rdheader(str(record_base))
    annotation = wfdb.rdann(str(record_base), "atr")
    lead_map = select_leads(list(header.sig_name), spec)[1]
    raw = wfdb.rdrecord(str(record_base), channels=lead_map["channel_indices"])
    clean_signal = resample_channels(raw.p_signal, raw.fs)
    rng = np.random.default_rng(seed)
    signal = perturb(clean_signal, condition, rng)
    reference = [(int(round(sample * TARGET_SAMPLE_RATE_HZ / raw.fs)), symbol) for sample, symbol in zip(annotation.sample, annotation.symbol) if symbol in detector.R_PEAK_SYMBOLS]
    all_reference_peaks = np.asarray([peak for peak, _ in reference], dtype=np.int64)
    accepted = load_pvc_windows(record_base, spec, lead_count=2)
    accepted_peaks = accepted["canonical_r_peak_samples"]
    labels = accepted["labels"].astype(np.int8)
    valid = (accepted_peaks >= HALF_WINDOW) & (accepted_peaks + HALF_WINDOW < len(signal))
    accepted_peaks, labels = accepted_peaks[valid], labels[valid]
    oracle_windows = np.asarray([normalise_window(signal[p - HALF_WINDOW:p + HALF_WINDOW]) for p in accepted_peaks], dtype=np.float32)
    oracle_rr = rr_features(accepted_peaks, all_reference_peaks)
    oracle_prob = core.apply_scaler(scaler, base.tflite_predict(model, oracle_windows, oracle_rr)).astype(np.float32) if len(oracle_windows) else np.empty(0, dtype=np.float32)
    oracle_pred = (oracle_prob >= THRESHOLD).astype(np.int8)
    detected = detector.causal_pan_tompkins(signal[:, 0], TARGET_SAMPLE_RATE_HZ)
    matches, missed, unmatched = detector.match_peaks(reference, detected, TOLERANCE_SAMPLES)
    auto_indices = [i for i, peak in enumerate(detected) if peak.peak_sample >= HALF_WINDOW and peak.peak_sample + HALF_WINDOW < len(signal)]
    auto_peaks = np.asarray([detected[i].peak_sample for i in auto_indices], dtype=np.int64)
    auto_windows = np.asarray([normalise_window(signal[p - HALF_WINDOW:p + HALF_WINDOW]) for p in auto_peaks], dtype=np.float32)
    auto_rr = rr_features(auto_peaks, np.asarray([peak.peak_sample for peak in detected], dtype=np.int64))
    auto_prob = core.apply_scaler(scaler, base.tflite_predict(model, auto_windows, auto_rr)).astype(np.float32) if len(auto_windows) else np.empty(0, dtype=np.float32)
    auto_pred = (auto_prob >= THRESHOLD).astype(np.int8)
    auto_by_detection = {index: (auto_prob[pos], auto_pred[pos]) for pos, index in enumerate(auto_indices)}
    label_by_peak = {int(p): int(label) for p, label in zip(accepted_peaks, labels)}
    auto_labels, auto_predictions, auto_positive_samples = [], [], []
    for ref_index, (ref_peak, symbol) in enumerate(reference):
        if symbol not in {"N", "V"} or ref_peak not in label_by_peak:
            continue
        detection_index = matches.get(ref_index)
        if detection_index is not None and detection_index in auto_by_detection:
            _, prediction = auto_by_detection[detection_index]
            auto_labels.append(label_by_peak[ref_peak]); auto_predictions.append(int(prediction))
            if prediction:
                auto_positive_samples.append(ref_peak)
    for detection_index in unmatched:
        if detection_index in auto_by_detection and auto_by_detection[detection_index][1]:
            auto_positive_samples.append(detected[detection_index].peak_sample)
    duration_seconds = len(signal) / TARGET_SAMPLE_RATE_HZ
    oracle_policy = count_policy_escalations(accepted_peaks, oracle_prob, duration_seconds)
    auto_positive_samples = sorted(auto_positive_samples)
    auto_policy = count_policy_escalations(np.asarray(auto_positive_samples, dtype=np.int64), np.ones(len(auto_positive_samples), dtype=np.float32), duration_seconds)
    oracle_binary = binary(labels, oracle_pred) if len(labels) else None
    automatic_binary = binary(np.asarray(auto_labels, dtype=np.int8), np.asarray(auto_predictions, dtype=np.int8)) if auto_labels else None
    unmatched_positive_events = sum(1 for i in unmatched if i in auto_by_detection and auto_by_detection[i][1])
    if automatic_binary is not None and unmatched_positive_events:
        automatic_binary["fp"] += unmatched_positive_events
        automatic_binary["pvc_precision"] = automatic_binary["tp"] / max(automatic_binary["tp"] + automatic_binary["fp"], 1)
        automatic_binary["pvc_recall"] = automatic_binary["tp"] / max(automatic_binary["tp"] + automatic_binary["fn"], 1)
        automatic_binary["pvc_f1"] = 2 * automatic_binary["pvc_precision"] * automatic_binary["pvc_recall"] / max(automatic_binary["pvc_precision"] + automatic_binary["pvc_recall"], 1e-12)
        automatic_binary["specificity"] = automatic_binary["tn"] / max(automatic_binary["tn"] + automatic_binary["fp"], 1)
    metrics = {
        "record_key": f"{source}:{record}", "source": source, "condition": condition["name"], "seed": seed,
        "duration_seconds": duration_seconds, "reference_beat_count": int(len(labels)),
        "oracle": oracle_binary, "automatic_matched": automatic_binary,
        "r_peak": {"tp": len(matches), "fp": len(unmatched), "fn": len(missed), "sensitivity": len(matches) / max(len(matches) + len(missed), 1), "ppv": len(matches) / max(len(matches) + len(unmatched), 1), "f1": 2 * len(matches) / max(2 * len(matches) + len(unmatched) + len(missed), 1)},
        "oracle_policy": oracle_policy, "automatic_policy": auto_policy,
        "automatic_positive_events": len(auto_positive_samples), "unmatched_positive_events": unmatched_positive_events,
    }
    arrays = {f"{source}__{record}__{condition['name']}__oracle_probability": oracle_prob, f"{source}__{record}__{condition['name']}__automatic_probability": auto_prob}
    return metrics, arrays


def aggregate(rows: list[dict]) -> dict:
    out = {"records": len(rows), "r_peak": {}, "oracle": None, "automatic_matched": None, "oracle_service_escalations_per_hour": 0.0, "automatic_service_escalations_per_hour": 0.0}
    for key in ("tp", "fp", "fn"):
        out["r_peak"][key] = int(sum(row["r_peak"][key] for row in rows))
    tp, fp, fn = out["r_peak"]["tp"], out["r_peak"]["fp"], out["r_peak"]["fn"]
    out["r_peak"].update({"sensitivity": tp / max(tp + fn, 1), "ppv": tp / max(tp + fp, 1), "f1": 2 * tp / max(2 * tp + fp + fn, 1)})
    for name in ("oracle", "automatic_matched"):
        valid = [row[name] for row in rows if row[name] is not None]
        if valid:
            counts = {key: int(sum(item[key] for item in valid)) for key in ("tn", "fp", "fn", "tp")}
            out[name] = binary(np.repeat([0, 1], [counts["tn"] + counts["fp"], counts["fn"] + counts["tp"]]), np.concatenate([np.repeat([0, 1], [counts["tn"], counts["fp"]]), np.repeat([0, 1], [counts["fn"], counts["tp"]])]))
    total_hours = sum(row["duration_seconds"] for row in rows) / 3600.0
    out["oracle_service_escalations_per_hour"] = sum(row["oracle_policy"]["request_review"] for row in rows) / max(total_hours, 1e-12)
    out["automatic_service_escalations_per_hour"] = sum(row["automatic_policy"]["request_review"] for row in rows) / max(total_hours, 1e-12)
    return out


def bootstrap(rows: list[dict], name: str) -> dict:
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    values = []
    for _ in range(BOOTSTRAP_RESAMPLES):
        sampled = [rows[int(i)] for i in rng.integers(0, len(rows), len(rows))]
        total_hours = sum(row["duration_seconds"] for row in sampled) / 3600.0
        values.append(sum(row[name]["request_review"] for row in sampled) / max(total_hours, 1e-12))
    return {"bootstrap_resamples": BOOTSTRAP_RESAMPLES, "seed": BOOTSTRAP_SEED, "ci_95": [float(np.quantile(values, .025)), float(np.quantile(values, .975))]}


def flatten(rows: list[dict]) -> list[dict]:
    flat = []
    for row in rows:
        item = {"record_key": row["record_key"], "source": row["source"], "condition": row["condition"], "seed": row["seed"], "duration_seconds": row["duration_seconds"], "reference_beat_count": row["reference_beat_count"], "automatic_positive_events": row["automatic_positive_events"], "unmatched_positive_events": row["unmatched_positive_events"]}
        item.update({f"r_peak_{key}": value for key, value in row["r_peak"].items()})
        for prefix in ("oracle", "automatic_matched"):
            if row[prefix] is not None:
                item.update({f"{prefix}_{key}": value for key, value in row[prefix].items()})
        for prefix in ("oracle_policy", "automatic_policy"):
            item.update({f"{prefix}_{key}": value for key, value in row[prefix].items()})
        flat.append(item)
    return flat


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=Path("models/gate_s2_int8_tf215_run1/model_int8.tflite"))
    parser.add_argument("--calibration", type=Path, default=Path("models/gate_s2_int8_tf215_run1/calibration.json"))
    parser.add_argument("--freeze-manifest", type=Path, default=Path("results/gate_s2_int8_tf215_run1/manifest.json"))
    parser.add_argument("--record-manifest", type=Path, default=Path("results/experiment0/record_manifest.csv"))
    parser.add_argument("--data-root", type=Path, default=Path("."))
    parser.add_argument("--result-dir", type=Path, default=Path("results/experiment6"))
    parser.add_argument("--conditions", nargs="+", default=None, help="Registered condition names to execute")
    parser.add_argument("--sources", nargs="+", default=None, choices=sorted(EXPECTED), help="Registered source keys to execute")
    parser.add_argument("--allow-frozen-robustness-evaluation", action="store_true")
    args = parser.parse_args()
    if not args.allow_frozen_robustness_evaluation:
        parser.error("Experiment 6 requires --allow-frozen-robustness-evaluation")
    if args.result_dir.exists():
        raise FileExistsError(f"Experiment 6 output already exists: {args.result_dir}")
    if (sha256(args.model), sha256(args.calibration), sha256(args.freeze_manifest)) != (MODEL_SHA256, CALIBRATION_SHA256, MANIFEST_SHA256):
        raise ValueError("Frozen Gate S2 artifact hash mismatch")
    calibration = json.loads(args.calibration.read_text(encoding="utf-8"))
    manifest = json.loads(args.freeze_manifest.read_text(encoding="utf-8"))
    if manifest.get("status") != "passed" or float(calibration.get("threshold", -1)) != THRESHOLD:
        raise ValueError("Gate S2 status or frozen threshold mismatch")
    selected_conditions = CONDITIONS if args.conditions is None else [condition for condition in CONDITIONS if condition["name"] in args.conditions]
    unknown_conditions = sorted(set(args.conditions or []) - {condition["name"] for condition in CONDITIONS})
    if unknown_conditions or not selected_conditions:
        raise ValueError(f"Unknown or empty condition selection: {unknown_conditions}")
    selected_sources = set(args.sources or EXPECTED)
    args.result_dir.mkdir(parents=True)
    protocol = {"experiment": "experiment_6_signal_robustness", "status": "registered_execution", "started_at_utc": datetime.now(timezone.utc).isoformat(), "candidate": "P0/O1", "model_sha256": MODEL_SHA256, "calibration_sha256": CALIBRATION_SHA256, "freeze_manifest_sha256": MANIFEST_SHA256, "threshold": THRESHOLD, "sources": {key: EXPECTED[key] for key in sorted(selected_sources)}, "conditions": selected_conditions, "base_seed": BASE_SEED, "r_peak_detector": "existing causal Pan-Tompkins-style implementation", "r_peak_match_tolerance_ms": 150.0, "policy": "policy-v1 rolling 30-second high-risk deque; three events trigger request_review", "primary_path": "automatic R-peak and fixed int8 inference", "diagnostic_path": "oracle annotation windows", "prohibited_operations": ["retraining", "calibration fitting", "threshold selection", "detector tuning", "model selection", "post-hoc perturbation selection"], "external_data_note": "SVDB and NSRDB are frozen robustness extensions; no selection or tuning follows", "bootstrap": {"resamples": BOOTSTRAP_RESAMPLES, "seed": BOOTSTRAP_SEED}, "write_once": True}
    write_json(args.result_dir / "protocol.json", protocol)
    write_json(args.result_dir / "perturbation_manifest.json", {"conditions": selected_conditions, "base_seed": BASE_SEED, "seed_rule": "base_seed + global_condition_index*10000 + record_index"})
    scaler = experiment3.frozen_scaler(calibration)
    records = [row for row in records_from_manifest(args.record_manifest) if row["source"] in selected_sources]
    all_rows, arrays, summaries = [], {}, {}
    global_condition_index = {item["name"]: index for index, item in enumerate(CONDITIONS)}
    for condition in selected_conditions:
        condition_index = global_condition_index[condition["name"]]
        rows = []
        for record_index, row in enumerate(records):
            seed = BASE_SEED + condition_index * 10000 + record_index
            metrics, archive = evaluate_record(row, args.data_root, args.model, scaler, condition, seed)
            rows.append(metrics); arrays.update(archive)
            print(f"[{condition['name']}] [{record_index + 1}/{len(records)}] {metrics['record_key']}", flush=True)
        summaries[condition["name"]] = {"condition": condition, "all_sources": aggregate(rows), "by_source": {source: aggregate([row for row in rows if row["source"] == source]) for source in EXPECTED}, "record_bootstrap_automatic_service_escalations_per_hour": bootstrap(rows, "automatic_policy"), "record_bootstrap_oracle_service_escalations_per_hour": bootstrap(rows, "oracle_policy")}
        all_rows.extend(rows)
    flat = flatten(all_rows)
    with (args.result_dir / "per_record_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=sorted({key for row in flat for key in row})); writer.writeheader(); writer.writerows(flat)
    np.savez_compressed(args.result_dir / "per_record_predictions.npz", **arrays)
    summary = {"experiment": protocol["experiment"], "status": "complete", "completed_at_utc": datetime.now(timezone.utc).isoformat(), "frozen_configuration_verified": True, "condition_count": len(selected_conditions), "record_count_per_condition": len(records), "conditions": summaries, "artifacts": {"protocol": str(args.result_dir / "protocol.json"), "perturbation_manifest": str(args.result_dir / "perturbation_manifest.json"), "per_record_metrics": str(args.result_dir / "per_record_metrics.csv"), "per_record_predictions": str(args.result_dir / "per_record_predictions.npz")}, "source_sha256": sha256(Path(__file__)), "dependencies": {"python": sys.version, "platform": platform.platform(), "numpy": np.__version__, "wfdb": wfdb.__version__}, "post_evaluation_rule": "No model, detector, calibration, threshold, quantization, preprocessing, lead profile, or seed change may be selected from these robustness results."}
    write_json(args.result_dir / "summary.json", summary)
    write_json(args.result_dir / "integrity_verification.json", {"model_sha256": sha256(args.model), "calibration_sha256": sha256(args.calibration), "freeze_manifest_sha256": sha256(args.freeze_manifest), "source_sha256": sha256(Path(__file__)), "status": "verified"})
    print(json.dumps({"status": "complete", "summary": str(args.result_dir / "summary.json"), "conditions": len(selected_conditions), "records_per_condition": len(records)}, indent=2))


if __name__ == "__main__":
    main()
