# Research Status

Status updated: 13 October 2026. The last tagged release is `v0.1.0-research-release`.

## Verified in the Local Research Record

- Experiments 0-6 have recorded artifacts.
- The software-selected configuration is M1/L2 with P0/O1.
- Gate S2 passed under the explicitly selected TensorFlow 2.15.1 runtime.
- Frozen SVDB evaluation and NSRDB false-alarm evaluation completed without
  subsequent tuning or selection.
- Automatic R-peak evaluation completed with a preserved oracle-to-automatic
  degradation analysis.
- Experiment 6 Part 1 and Part 2 completed under the frozen model, threshold,
  and policy, with integrity verification.

## Key Frozen Evidence

- Gate S2 support-aware record-macro PVC F1: `0.8335`.
- Gate S2 support-aware PVC recall: `0.9075`.
- Gate S2 int8 artifact size: `11,240` bytes.
- SVDB support-aware record-macro PVC F1: `0.6736`.
- NSRDB false PVC detections: `1,113` over `437.49` hours.
- NSRDB aggregate policy-v1 false service escalations: `0.606/hour`;
  record-bootstrap upper confidence limit `1.638/hour`, with worst-record
  behavior not uniformly satisfying the target.
- Automatic R-peak PVC recall: `0.7762`, compared with `0.8741` for reference
  peaks in the same frozen evaluation.

## Software Loop Validation

- Experiment 8A completed over local MQTT v5 QoS 1 with 1,200 baseline windows
  across 30 sessions. All baseline events were acknowledged; 1%, 5%, and 10%
  loss recovery and bounded outage recovery had zero permanent event loss.
- Accepted-event audit completeness was 100%; rejected-event reason-code
  completeness was 100%; duplicate action rate was zero; gateway restart
  recovered the WAL outbox; the local loop remained available during simulated
  Internet outage.
- Experiment 7 completed 1,020 inference windows and 30 sessions. The int8
  artifact was 11,240 bytes, p95 neural inference was 0.4976 ms, and p95
  logical acquisition-to-local-decision latency was 423.79 ms.
- Gate V passed using matching MQTT transport, frozen model hash, threshold,
  policy, contract version, and software-only evidence labels.

These are software-simulated/runtime results. They do not establish physical
ECG acquisition, hardware latency, energy consumption, wearable suitability,
clinical efficacy, regulatory approval, or production security.

## Not Complete

The literature matrix and English/Chinese working drafts are available in
`docs/literature-matrix.md` and `manuscript/`. Four evidence-linked figures and
two tables are drafted. Final citation and metadata audit, figure review,
internal review, revision, and submission packaging remain open. Experiment 8B
and Gate H are outside the advisor-approved software-only scope. The project
has software-loop validation, not measured physical deployment evidence.

## Experiment 6 Robustness Evidence

- Part 1: baseline wander, 50/60 Hz interference, and 20/10/5 dB muscle noise.
- Part 2: 0.5x/1.0x/2.0x amplitude scaling, 50-sample loss, 5 ms timing
  jitter, and single-channel dropout.
- Strong muscle noise substantially reduced PVC recall; primary-channel
  dropout prevented valid causal R-peak processing.
- Results are descriptive frozen-model evidence; no model, threshold,
  calibration, detector, or preprocessing selection followed.

The study validates a software-simulated two-tier local-edge service loop
consisting of a replay-based ECG acquisition endpoint and a local gateway
process. The results do not establish physical ECG acquisition, hardware
latency, energy consumption, or wearable deployment suitability.

## Post-Gate-V Strengthening and Synthesis

- Ten fixed MIT-BIH/INCART fragments were replayed through the same local MQTT
  v5 path in `results/experiment8a_real_replay/`: 300/300 windows accepted,
  100% accepted-event audit completeness, and no transport callback errors.
- The gateway replay field is a packet-local peak proxy, not the Experiment 5
  causal detector; this is input-realism evidence, not detector accuracy or
  physical acquisition evidence.
- `results/cross_layer_attribution/` contains a six-layer, denominator-aware
  synthesis. It deliberately does not add ECG peak errors and service-event
  failures into one percentage.
- `docs/literature-matrix.md` and `manuscript/draft.md` provide the initial
  related-work matrix and paper draft. They are not final until each source,
  numerical claim, figure, and table passes internal integrity review.
- The exploratory causal-detector-to-MQTT bridge received 500/500 raw packets;
  233/233 eligible events from eight of ten fragments had terminal ACK and
  complete audit lineage. Two INCART fragments produced no eligible events.
- During fixed channel-1 loss, both tested interruption intervals had zero
  eligible events and zero reason-coded reacquire ACKs. A no-event fallback is
  therefore not demonstrated.
