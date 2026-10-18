# Edge ECG Digital Service Loop Research Plan

## Material Passport

- Origin Skill: `ars-codex:academic-research-suite`
- Origin Route: `academic-pipeline` Stage 1 / methodology planning
- Origin Date: 2026-08-02
- Version: `research_plan_v7_cfp_writing_and_bounded_replay`
- Last Updated: 2026-10-18
- Verification Status: `PARTIALLY VERIFIED`
- Verified Evidence: official special-issue CFP and IEEE Internet of Things Magazine author guidelines, advisor-approved two-tier logical edge architecture decision, local source code, Experiment 0 audit, Experiment 1/2 development reports, Experiment 2.5/2.6/2.6R and final revalidation evidence, Gate S2 direct-int8 software freeze, frozen SVDB and NSRDB reports, final automatic R-peak evaluation, Experiment 6 robustness and fault-injection reports, Experiment 7 runtime benchmark, Experiment 8A MQTT v5 service-loop benchmark, Gate V decision, completed packet-local-proxy real ECG replay, completed exploratory causal-detector-to-MQTT bridge and channel-1-loss diagnostic, cross-layer attribution synthesis, focused literature verification supporting Experiment 2.5, the targeted primary-source check recorded in `docs/literature-matrix.md` on 9 October 2026, and the bilingual six-section manuscript/DOCX structure, numerical cross-check, and rendered figure review recorded in `docs/manuscript-release-check.md` on 18 October 2026.
- Not Yet Verified: exhaustive literature-level novelty wording, author-side final citation metadata and internal scientific review, author identities/ORCIDs, and submission packaging. A no-event reacquisition fallback is **not demonstrated** and must remain an observed limitation.

## 1. Purpose of This File

This file is the executable research charter for the project. It defines the research question, scope, data roles, experimental sequence, service-loop prototype, evidence gates, paper narrative, and submission schedule.

Future work must update the status table and evidence paths in this file after each experiment. Planned contributions must not be rewritten as findings until the corresponding result artifact exists and passes its gate.

## 2. Target Venue and Non-Negotiable Scope

- Venue: IEEE Internet of Things Magazine
- Special Issue: **Digital Service Loops for IoT-Enabled Connected Healthcare Systems**
- Official CFP: <https://www.comsoc.org/publications/magazines/ieee-internet-things-magazine/cfp/digital-service-loops-iot-enabled>
- Official author guidelines: <https://www.comsoc.org/publications/magazines/ieee-internet-things-magazine/policies-guidelines>
- Manuscript submission deadline: **31 October 2026**
- Initial decision date: 31 January 2027
- Planned publication: Third Quarter 2027

### Magazine Submission Constraints

- Main text from Introduction through Conclusion must be at most **4,500 words**; title, author information, abstract, figures, tables, captions, acknowledgements, references, and biographies are excluded by the author guidelines.
- Published figures and tables combined must total at most **six**. Do not evade this cap through crowded multi-panel figures or undersized tables.
- Use at most **15 references**, numbered in citation order. Verify every cited claim against its source; include an access date for online references as required by the author guidelines.
- Write for a broad IoT/communications readership in an accessible, tutorial style. Avoid mathematical notation; the guidelines permit at most two simple equations only when justified.
- The magazine does not require a specific submission template. Prepare an editable final manuscript and separate figure source files; confirm ORCIDs for all authors and keep any author biographies within 150 words each.
- Check the applicable special-issue article type and final portal requirements before submission. The deadline is **31 October 2026**.

The CFP defines a digital service loop as a continuous cycle of sensing, interpretation, decision-making, execution, and validation. It lists edge/fog/cloud integration among relevant deployment patterns, but it does not require every paper to use every tier. This project adopts an advisor-approved two-tier local-edge architecture: an ECG acquisition endpoint plus a local edge gateway. Cloud computation is not required for the operational loop.

Therefore, this project must not be framed as merely a higher-accuracy ECG classifier. The PVC model is the interpretation component inside a verifiable service loop:

```text
Simulated ECG acquisition endpoint: replay, timestamps, sequence numbers, and short local buffering
  -> local endpoint-to-gateway transport
  -> local gateway process: signal quality, resampling, and causal R-peak interpretation
  -> calibrated PVC-risk event
  -> gateway-local policy decision
  -> safe service action
  -> acknowledgement to the acquisition endpoint and outcome validation
  -> auditable feedback and rule update
```

### Advisor-Approved Deployment Boundary

- Tier 1 is the **simulated ECG acquisition endpoint**. A replay process emits one or two configured channels, attaches timing and sequence metadata, maintains a bounded simulated buffer, transmits locally, and receives monitor/reacquire acknowledgements.
- Tier 2 is the **local gateway process**. It reconstructs the simulated stream, evaluates signal quality, resamples to 360 Hz, detects R peaks, extracts windows, runs calibrated PVC inference, applies the versioned service policy, records the audit trail, and returns acknowledgement.
- The latency-critical sensing-to-decision-to-feedback loop must close locally between these two tiers even when Internet connectivity is absent.
- A remote caregiver or telehealth review request may be an optional outbound action after the local decision. Remote review is not a model-inference tier and is not required to close the measured local loop.
- The replay-based acquisition endpoint and local transport are software simulation components for the complete study. They must be labelled simulated and cannot support claims about physical electrode acquisition latency, analogue-front-end energy, hardware resource use, or wearable deployment.

The study validates a software-simulated two-tier local-edge service loop
consisting of a replay-based ECG acquisition endpoint and a local gateway
process. The results do not establish physical ECG acquisition, hardware
latency, energy consumption, or wearable deployment suitability.

### In-Scope Service Actions

- Continue local monitoring.
- Request ECG reacquisition when signal quality is inadequate.
- Buffer and transmit a short ECG segment for remote review.
- Create a non-diagnostic caregiver or telehealth review request after a predefined event pattern.
- Record acknowledgement, delivery failure, retry, review status, and policy version.
- Return monitor/reacquire commands from the local gateway to the acquisition endpoint.

### Explicitly Out of Scope

- Autonomous medical diagnosis.
- Automatic medication, defibrillation, or other therapeutic actuation.
- Claims of clinical efficacy, regulatory approval, or patient outcome improvement.
- A model that dynamically accepts arbitrary lead counts or arbitrary lead semantics.
- Online self-training from unverified service feedback.
- Using SVDB or NSRDB to tune model architecture, calibration, thresholds, or preprocessing.
- Cloud inference, cloud orchestration, or Internet availability on the latency-critical path.
- Treating a dataset replay process as evidence of physical ECG acquisition performance.

### Software-First Sequencing and Dual-Freeze Policy

This project uses two separate evidence gates. **Gate S: Software Evaluation Freeze** fixes the architecture, development sources, seed policy, weights, calibration, threshold, lead mapping, preprocessing, int8 artifact, and manifest before frozen external model evaluation. Gate S does not require physical hardware and must not be described as a measured device-deployment result.

**Gate V: Software Loop Validation** fixes the simulated endpoint, simulated local transport, gateway runtime, queue configuration, fault-injection profile, and clock method. Gate V requires Experiment 7 and Experiment 8A evidence before the paper may claim a validated software-simulated two-tier local-edge service loop.

Experiments 3-6 may follow Gate S before Gate V. SVDB and NSRDB must never be used to choose architecture, calibration, threshold, quantization, lead profile, or any fallback. No physical hardware experiment is required for this research version; any future hardware study is separate and exploratory.

## 3. Current Project Status

| Component | Status | Evidence | Interpretation |
|---|---|---|---|
| MIT-BIH record-level baseline | Complete | `models/pvc_calibrated_metrics.json` | Historical single-database baseline |
| Waveform + pre-RR baseline | Complete | `models/pvc_rr_calibrated_metrics.json` | Causal rhythm-feature comparison |
| Waveform + pre/post-RR baseline | Complete | `models/pvc_prepost_rr_calibrated_metrics.json` | Delayed-decision upper comparison, not preferred edge model |
| Frozen INCART evaluation | Complete, historical | `models/incart_external_frozen_metrics.json` | Cannot remain final external evidence after INCART enters training |
| Automatic R-peak exploratory evaluation | Complete, historical | `models/streaming_rpeak_*_metrics.json` | Shows pipeline degradation; the final-model evaluation is complete in Experiment 5 |
| Multi-source audit and preprocessing contract | Complete | `results/experiment0/` | Experiment 0 passed |
| Advisor-approved deployment architecture | Software identities and MQTT v5 loopback evidence complete; physical deployment out of scope | AGENTS.md Section 8, `src/service_loop/`, `results/experiment7/`, `results/experiment8a/`, `results/gate_v/decision.json` | Simulated ECG acquisition endpoint plus local gateway process; cloud-independent critical loop |
| Multi-source model training | Complete | `results/experiment1/runs.csv`, `results/experiment1/summary.json`, `results/experiment1/per_record_predictions/` | M0/M1/M2 each completed with five outer folds and three fixed seeds; development evidence only. |
| Single- versus two-lead comparison | Complete; L2 is the software-frozen lead profile | `results/experiment2/summary.json`, `results/experiment2/completion.json`, `results/experiment2/runs.csv`, `results/experiment2/per_record_predictions/` | L1/L2 each completed with five outer folds and three fixed seeds. L2 is retained for the software-simulated endpoint and gateway loop; no physical acquisition claim follows. |
| Pre-freeze model optimization | Complete; historical development decision | `results/experiment2_5/` | O1 was retained after bounded refinement; O2 increased PVC-free-record false positives. Gate S2 and frozen external evaluations subsequently completed without using SVDB/NSRDB for selection. |
| Experiment 2.6 controlled refinement | Complete; P0 selected, therefore O1 retained | `results/experiment2_6/protocol.json`, `results/experiment2_6/runs.csv`, `results/experiment2_6/summary.json` | P1 did not improve paired PVC-record F1 and slightly increased PVC-free false decisions; P2/P3 failed the Stage A PVC-free safety gate. No additional architecture search is permitted. |
| Experiment 2.6R Recall-stability revision | Complete; no candidate advanced beyond Stage A | `results/experiment2_6r/` | R1 violated the PVC-free safety gate; R2 met recall and safety but failed F1 non-inferiority; R3 found no feasible inner-fold safety threshold and reproduced P0. P0/O1 remains retained and model search stops. |
| Final-architecture M0/M1/M2 and L1/L2 revalidation | Complete; M1/L2 retained | `results/final_revalidation/summary.json`, `results/final_revalidation/runs.csv` | 60 runs completed with five record-level folds and three fixed seeds. M1/L2 reproduces the P0/O1 metrics; M1 versus M0 paired F1 CI crosses zero; M2 increases recall but materially reduces F1 and increases PVC-free false decisions; L2 improves paired F1 over L1 with a positive bootstrap lower bound. No external data were accessed. |
| Gate S software-freeze attempts | Conversion-only compatibility checks complete; Gate S remains closed | `results/software_freeze_gate_s_retry6/`, `results/gate_s_qat_retry2/`, `results/gate_s_converter_tf216/`, `results/gate_s_converter_tf215/`, `results/gate_s_converter_tf215_rebuild_calibrated/` | The original full-int8 run failed p99 0.163 (extreme-coverage preflight 0.111); fixed-range fake QAT reduced p99 to 0.0958 but did not pass. TensorFlow 2.16 failed internally during conversion; TensorFlow 2.15 converted the unchanged source weights but p99 was 0.1552. All failed artifacts are preserved, no external data were accessed, and no model/threshold choice changed. |
| Gate S standard QAT remediation | Complete; failed multiple immutable equivalence criteria | `results/gate_s_tfmot_qat/protocol.json`, `results/gate_s_tfmot_qat_run3/manifest.json`, `results/gate_s_tfmot_qat_run3/int8_equivalence.json` | The one registered standard TFMOT QAT attempt retained 3,506 trainable parameters and used only M1 development records, five folds, seed 20260803, 19 epochs, 150 steps/epoch, and OOF-only calibration/threshold selection. Its int8 artifact was 11,000 bytes, but agreement was 0.983, mean error 0.0219, p99 error 0.2471, and F1 loss 0.0232; only size and Recall-loss criteria passed. The stopping rule is reached: retain P0/O1, stop all model/quantization searches, and keep external evaluation locked. |
| Gate S2 direct int8 calibration amendment | Complete; passed under the explicitly selected TensorFlow 2.15.1 runtime | `results/gate_s2_int8/protocol.json`, `results/gate_s2_int8/execution_failure.json`, `results/gate_s2_int8_tf215_run1/int8_direct_evaluation.json`, `results/gate_s2_int8_tf215_run1/manifest.json` | The TensorFlow 2.16.1 run remains an aborted toolchain record. The one fixed TensorFlow 2.15.1 rerun completed five int8 OOF folds and a final int8 artifact, using MIT-BIH + INCART only. Support-aware macro F1 was 0.8335, recall 0.9075, precision 0.8336, record-macro AUPRC 0.8969, Brier 0.0236, and PVC-free false decisions 83 versus P0 control 87; artifact size was 11,240 bytes and held float/int8 decision agreement was 1.000. All registered Gate S2 criteria passed. The original Gate S p99 failure remains disclosed as a descriptive paired diagnostic (Gate S2 p99 0.0792) and is not reclassified. |
| Frozen SVDB evaluation | Complete; frozen int8 P0/O1 evaluated once on SVDB | `results/experiment3/protocol.json`, `results/experiment3/summary.json`, `results/experiment3/per_record_metrics.csv`, `results/experiment3/integrity_verification.json` | Under the passed Gate S2 artifact, fixed calibration, and threshold `0.49`, the oracle-annotation SVDB evaluation yielded support-aware record-macro PVC F1 `0.6736` (record-bootstrap 95% CI `0.5945` to `0.7493`), recall `0.7154`, precision `0.7411`, record-macro AUPRC `0.8087`, Brier `0.0323`, and pooled confusion matrix TN/FP/FN/TP `158070/4196/2660/7280`. This is an isolated cross-database holdout, not a pristine blind test; no tuning or selection followed. |
| NSRDB false-alarm evaluation | Complete; frozen int8 P0/O1 evaluated once on NSRDB | `results/experiment4/protocol.json`, `results/experiment4/summary.json`, `results/experiment4/per_record_false_alarms.csv`, `results/experiment4/integrity_verification.json` | At fixed threshold `0.49`, 1,113 false PVC detections occurred over 1,729,496 annotated `N` beats and 437.49 h: false-positive rate `0.000644` and 2.544 false PVC detections/h. Under the existing `policy-v1` three-events-in-30-s aggregation, the overall false service-escalation rate was `0.606/h` (aggregate target <= `1/h`), but the record-bootstrap 95% CI was `0.037` to `1.638/h` and worst record `nsrdb:16272` was `9.0/h`; the target is therefore not uniformly supported across records. Signal-quality and automatic-R-peak relationships remain deferred to Experiment 5. No tuning or selection followed. |
| Final automatic R-peak evaluation | Complete; frozen int8 P0/O1 evaluated with the existing causal detector | `results/experiment5_retry2/protocol.json`, `results/experiment5_retry2/summary.json`, `results/experiment5_retry2/per_record_metrics.csv`, `results/experiment5_retry2/per_record_predictions.npz` | Across 219 records, 218 had eligible N/V classifier windows; `mitdb:232` had none after the fixed boundary exclusion and remains detector-only. At the immutable threshold `0.49`, automatic R-peak detection had sensitivity `0.9522`, PPV `0.9956`, and F1 `0.9734`. Pooled PVC recall fell from `0.8741` with reference peaks to `0.7762` with automatic peaks (F1 `0.8531` to `0.8078`); the PVC-miss decomposition was 3,325 unmatched V peaks, 317 window-mislocalizations, and 4,660 classifier-or-causal-RR errors. No detector, model, calibration, threshold, quantization, preprocessing, lead profile, or seed selection followed. Initial and retry-1 evaluator crashes are preserved under `results/experiment5/` and `results/experiment5_retry1/`; their boundary-case repairs did not change the frozen system. |
| Robustness and fault injection | Complete; Parts 1 and 2 passed frozen-artifact integrity verification | `results/experiment6_part1/`, `results/experiment6_part2/` | Part 1 covers clean baseline, baseline wander, 50/60 Hz interference, and 20/10/5 dB muscle noise. Part 2 covers 0.5x/1.0x/2.0x amplitude scaling, one 50-sample loss interval per record, 5 ms timing jitter, and single-channel dropout. Amplitude scaling was invariant after per-window normalization; sample loss and 5 ms jitter had minimal pooled effect. Dropping channel 2 gave automatic PVC F1 0.8377 versus clean 0.8473; dropping channel 1 prevented the fixed channel-1 causal detector from producing eligible classifier events. The frozen system therefore requires channel-1 continuity or an explicit quality/reacquisition fallback. No model, detector, threshold, calibration, quantization, preprocessing, lead profile, or seed selection followed. |
| Software runtime and local-loop benchmark | Complete; MQTT v5 loopback | `results/experiment7/summary.json`, `results/experiment7/protocol.json` | 1,020 windows and 30 sessions; p95 neural inference 0.4976 ms and p95 logical acquisition-to-local-decision 423.79 ms; software-runtime evidence only. |
| Software-only local orchestration and feedback benchmark | Complete; MQTT v5 loopback | `results/experiment8a/summary.json`, `results/experiment8a/protocol.json` | 1,200 baseline windows across 30 sessions; loss/outage recovery, audit, restart, mismatch, and Internet-outage scenarios completed; software-simulation evidence only. |
| Post-Gate-V real ECG replay strengthening | Complete; exploratory and non-gating | `results/experiment8a_real_replay/` | Ten fixed MIT-BIH/INCART fragments, 300 windows, and 10 sessions passed local MQTT v5 replay; all windows were acknowledged and accepted-event audit completeness was 100%. The gateway field is a packet-local peak proxy, not the Experiment 5 causal detector; no physical or clinical claim follows. |
| Causal-detector-to-MQTT replay bridge | Complete; registered exploratory software run; linked-event criteria passed with fragment coverage limit | `results/experiment8a_causal_bridge/protocol.json`, `results/experiment8a_causal_bridge/summary.json`, `results/experiment8a_causal_bridge/per_fragment.json`, `results/experiment8a_causal_bridge/events.csv`, `results/experiment8a_causal_bridge/report.md` | On ten fixed clean development fragments, 500/500 MQTT raw packets arrived and 233/233 eligible causal-peak events from eight fragments had action, terminal ACK, and complete audit lineage. INCART I03/I04 produced zero detector peaks/events. Complete-fragment resampling preceded MQTT, and repeated-prefix adapter runtime is not Experiment 7 latency. Gate S2, Gate V, and external results are unchanged. |
| Channel-1-loss service diagnostic | Complete; no-event reacquisition fallback **not demonstrated** | `results/experiment8a_causal_bridge/per_fragment.json`, `results/experiment8a_causal_bridge/report.md` | Fixed 10–15 s channel-1 zeroing on MIT-BIH 100 and INCART I01 reduced eligible events 28→22 and 38→31. Both interruption intervals had zero eligible events and zero reason-coded reacquire ACKs. Report this as the current service limitation; do not change frozen policy or detector to obtain a pass. |
| Cross-layer error attribution synthesis | Complete; analysis of existing evidence, not a new model experiment | `results/cross_layer_attribution/` | Six layers are reported with layer-specific denominators and source hashes. The result is an error-attribution framework, not an additive error budget. |
| Literature novelty matrix and manuscript synthesis | Bilingual six-section drafts, editable DOCX files, localized vector figures, and page render review complete; author-side scientific and metadata review open | `docs/literature-matrix.md`, `docs/iotm-style-benchmark.md`, `docs/manuscript-release-check.md`, `manuscript/draft.md`, `manuscript/draft.zh-CN.md`, `manuscript/Edge_ECG_Service_Loop_English.docx`, `manuscript/Edge_ECG_Service_Loop_Chinese.docx`, `manuscript/figures/en/`, `manuscript/figures/zh-CN/` | Twelve working references retain read-scope and claim boundaries. Both drafts distinguish the primary packet-local-proxy benchmark from the exploratory causal bridge, including two zero-event fragments and the missing channel-loss feedback. Four figures and two Word-native tables meet the six-item cap. English main text is 1,879 words. Frozen numerical claims and page layout were checked; exhaustive novelty, author-side citation metadata, and internal scientific review remain pending. |
| Hardware deployment extension | Not applicable to current scope | Future work only | Physical endpoint, hardware gateway, energy, and wearable measurements are outside the current study. |

### Verified Historical Results

These numbers describe previous MIT-BIH-only models. They are baselines, not final paper results.

| Condition | PVC precision | PVC recall | PVC F1 | Specificity |
|---|---:|---:|---:|---:|
| Waveform only, nested calibration | 0.896 | 0.842 | 0.868 | 0.991 |
| Waveform + causal pre-RR | 0.887 | 0.894 | 0.890 | 0.989 |
| Waveform + pre/post-RR | 0.913 | 0.913 | 0.913 | 0.992 |
| Frozen pre/post-RR model on INCART | 0.840 | 0.832 | 0.836 | 0.979 |

The pre/post-RR model waits for the following R peak and is therefore unsuitable as the primary low-latency model. It remains an offline upper-comparison condition.

The exploratory streaming experiment showed a major oracle-to-automatic gap. On MIT-BIH, waveform-only PVC F1 fell from 0.898 with reference R peaks to 0.615 with automatic R peaks. On SVDB it fell from 0.416 to 0.295. This supports the need for an end-to-end loop evaluation but does not establish the final system result.

## 4. Research Question Brief

### Primary Research Question

**Under heterogeneous ECG domains and edge-resource constraints, can a software-simulated ECG acquisition endpoint and local gateway form an auditable, recoverable, low-latency, and measurable non-diagnostic PVC-risk service loop without cloud-dependent inference?**

### Sub-Questions

1. Does adding INCART and LTDDB to MIT-BIH training improve record-level development performance and frozen cross-database generalization without allowing long records or one source to dominate learning?
2. How much performance is lost when the final classifier is driven by causal automatic R peaks and realistic signal disturbances rather than reference annotations?
3. Can a software-simulated acquisition-endpoint-to-local-gateway-to-endpoint loop meet predefined latency, local-transport reliability, false-escalation, resource, recovery, and auditability requirements without cloud dependency?

All sub-questions inherit the same scope: adult public ECG databases, `N` versus `V` beat classification, fixed 360 Hz canonical gateway timing, fixed one- or two-channel model variants, a two-tier local-edge deployment, and non-diagnostic service escalation.

### FINER Assessment

| Criterion | Score | Rationale |
|---|---:|---|
| Feasible | 4/5 | All five databases are local and audited; model and software service-loop code exist. The remaining work is software benchmark and validation. |
| Interesting | 4/5 | It addresses the gap between annotation-centered ECG classification and operational connected-health services. |
| Novel | 3/5 | The integrated evidence design may be novel, but literature-level novelty requires a formal search before claiming it. |
| Ethical | 4/5 | Public secondary data and non-diagnostic actions reduce risk; clinical claims and autonomous treatment are excluded. |
| Relevant | 5/5 | Directly matches the CFP's edge, feedback-loop, reliability, and accountability themes. |
| **Average** | **4.0/5** | Proceed, subject to literature and software-loop validation gates. |

## 5. Planned Contribution Claims

These are hypotheses to be tested, not current findings.

1. **Two-tier local-edge service-loop architecture:** an explicit responsibility contract separates sensing, timestamping, buffering, and transport at the simulated ECG endpoint from interpretation, policy, audit, and acknowledgement at the local gateway.
2. **Versioned service contract and accountable orchestration:** events and actions retain endpoint/gateway identity, contract version, model hash, threshold, lead mapping, policy version, acknowledgement, reason code, and terminal state.
3. **Closed-loop recovery validation:** bounded loss, duplicate and out-of-order delivery, outage, mismatch, saturation, and gateway restart are evaluated without Internet-dependent loop closure.
4. **Multi-source PVC interpretation case:** the frozen M1/L2/P0/O1 int8 model and Experiments 0-6 provide the interpretation-component evidence rather than the paper's primary standalone contribution.
5. **Joint clinical and service benchmarking:** evaluation combines PVC metrics with false escalations per hour, simulated transport reliability, software latency decomposition, bandwidth, process memory/model size, recovery behavior, and audit completeness.

The paper must not claim novelty from using a 1D-CNN, Pan-Tompkins-style detection, resampling, Platt calibration, MQTT, or TFLite individually. The candidate novelty is the integrated, measurable, and auditable digital service loop and the evidence demonstrating its trade-offs.

### Contribution-Scope Decision (2026-10-06)

The paper's primary contribution order is now fixed as follows:

1. Two-tier local-edge responsibility contract and versioned service event contract.
2. Closed-loop recovery, acknowledgement, provenance, and auditability under controlled faults.
3. A **cross-layer error-attribution framework** that places existing sensing, signal/window, interpretation, transport, orchestration, and feedback results in one analysis. This is not called a quantitative error budget unless compatible denominators and a valid aggregation rule are demonstrated.
4. Joint clinical and service metrics using the frozen PVC interpretation component.

The following are explicitly deferred and must not be presented as completed contributions:

- `Evidence-Aware Policy`: retain frozen `policy-v1`; discuss multi-evidence policy as future work unless a separately registered post-Gate-V exploratory policy experiment is completed.
- FHIR or full healthcare semantic interoperability: retain the internal versioned service contract and state FHIR as a limitation/future direction.
- Formal verification: report tested operational invariants, not formal verification, unless a separate mechanical state-space or proof artifact is produced.

## 6. Methodology Blueprint

### Paradigm and Study Type

- Paradigm: pragmatic, quantitative systems research.
- Design: secondary-data machine-learning study plus prototype-based IoT systems benchmarking.
- Primary evidence: public annotated ECG databases and controlled service-loop fault injection.
- Human-subject status: no new human participants are planned. Local institutional requirements must still be checked before manuscript submission.
- Preregistration: recommended before Experiment 1 model selection and mandatory before unlocking final SVDB evaluation if the team wants confirmatory language.

### Units of Analysis

- Model-development split unit: record-level `split_group`, never individual beats.
- Known linked MIT-BIH records `201` and `202`: one split group.
- Clinical metric aggregation: pooled beats and record-level macro results, with the macro result treated as primary for generalization.
- Service metric aggregation: event, session/record, and fault-injection run.
- Software runtime metric aggregation: repeated inference or end-to-end loop runs after warm-up, with runtime and host configuration recorded.

### Validity Strategy

| Threat | Design Control |
|---|---|
| Beat-level leakage | Split complete records and linked-subject groups only |
| Test-set tuning | Freeze design, weights, calibration, and threshold before final SVDB run |
| LTDDB long-record dominance | Source-balanced, record-balanced, class-aware sampling |
| Database-specific lead semantics | Fixed documented mappings; separate one- and two-channel models |
| Sampling-rate confounding | Canonical 360 Hz across all conditions; no rate selection using SVDB |
| Long-record metric dominance | Report record-level macro metrics and record bootstrap intervals |
| Seed luck | Three fixed training seeds per candidate condition |
| Automatic R-peak coupling | Report oracle and automatic pipelines separately |
| Desktop latency mislabeling | Separate acquisition/packetization, local transport, mandatory post-R wait, gateway preprocessing/R-peak, neural inference, policy, and acknowledgement latency |
| Two-tier role ambiguity | Freeze simulated endpoint, local transport, and gateway responsibilities and identifiers before software benchmarking |
| Previously observed SVDB | Disclose as isolated external holdout, not pristine blind test |
| Simulated service actions | Label them prototype/fault-injection results, not clinical deployment outcomes |

## 7. Data and Preprocessing Contract

### Data Roles

| Database | Records | Native channels | Native rate | Role | Eligible N | Eligible V |
|---|---:|---|---:|---|---:|---:|
| MIT-BIH Arrhythmia | 48 | 2 | 360 Hz | Training/development | 75,017 | 7,129 |
| INCART | 75 | 12 | 257 Hz | Training/development, selected channels only | 150,346 | 20,006 |
| LTDDB | 7 | 2, one record has 3 | 128 Hz | Long-duration training supplement | 600,224 | 64,094 |
| SVDB | 78 | 2 | 128 Hz | Locked cross-database test | 162,266 | 9,940 |
| NSRDB | 18 | 2 | 128 Hz | Normal-rhythm evaluation only | 1,729,496 | 26 |

Training candidates contain 825,587 eligible `N` and 91,229 eligible `V` windows before balanced sampling.

### Fixed Preprocessing

- Canonical rate: 360 Hz.
- Resampling: polyphase resampling using the audited integer up/down ratios.
- Window: 300 samples centered on the R peak, 150 before and 150 after.
- Window duration: 0.8333 seconds.
- Mandatory post-R acquisition delay: 416.7 ms before detector and inference overhead.
- Labels: `N -> 0`, `V -> 1`; all other WFDB symbols excluded.
- Normalization: zero mean and unit standard deviation independently per channel and per window.
- No imputation or padding at record boundaries.

### Lead Mapping

| Variant | MIT-BIH | INCART | LTDDB/SVDB/NSRDB |
|---|---|---|---|
| One-channel primary | MLII; records 102/104 fall back to channel 0 | II | ECG1 |
| Two-channel ablation | MLII plus the other synchronized channel; 102/104 use both available channels | II + V1 | ECG1 + ECG2 |

The two-channel model means two fixed synchronized channels, not standardized 12-lead fusion. It must be described as a separate model with input shape `(300, 2)`.

### Immutable Audit Evidence

- `results/experiment0/preprocessing_contract.json`
- `results/experiment0/record_manifest.csv`
- `src/multisource_ecg.py`
- `src/07_multisource_data_audit.py`

## 8. System Architecture

### Tier 1: ECG Acquisition Endpoint

- Acquire one or two configured ECG channels at the declared native rate and lead profile.
- Attach endpoint pseudonym, monotonic sample sequence, acquisition timestamp, lead profile, and native sample rate.
- Maintain a bounded ring buffer for temporary local-link interruption and retransmission.
- Send packetized ECG samples or short ordered batches to the local gateway over one frozen transport profile.
- Receive monitor/reacquire acknowledgements and expose their terminal status.
- Do not perform PVC classification, autonomous diagnosis, or unverified online learning.

### Local Endpoint-to-Gateway Transport

- Freeze one primary local transport profile before the final benchmark, such as BLE, local Wi-Fi, or wired LAN/serial.
- Preserve sequence order, detect gaps and duplicates, and expose transport timestamps for latency decomposition.
- Define bounded retry, queue capacity, backpressure, stale-packet, and buffer-overrun behavior.
- The local loop must remain operational without Internet connectivity. Optional remote-review delivery is a separate non-critical egress path.

### Tier 2: Local Edge Gateway

- Reconstruct the configured one- or two-channel ECG stream.
- Apply causal streaming preprocessing and resampling to the 360 Hz canonical gateway timeline.
- Estimate signal quality and detect R peaks causally.
- Extract the fixed post-R window and run the int8 classifier.
- Apply frozen probability calibration, decision threshold, and versioned local service policy.
- Execute monitor/reacquire/buffer/review-request actions, retain the append-only audit record, and acknowledge the acquisition endpoint.
- Emit event summaries rather than continuously forwarding all raw ECG beyond the local system.

### Event Contract

Every accepted gateway event must include at least:

```json
{
  "event_id": "globally unique id",
  "acquisition_endpoint_pseudonym": "non-identifying endpoint id",
  "gateway_pseudonym": "non-identifying gateway id",
  "recorded_at": "UTC timestamp",
  "sample_sequence": "monotonic endpoint sequence or range",
  "transport_profile": "frozen local-link profile",
  "lead_profile": "one_channel or two_channel",
  "native_sample_rate_hz": "declared endpoint rate",
  "gateway_sample_rate_hz": 360,
  "signal_quality": "numeric score and status",
  "r_peak_source": "automatic",
  "pvc_probability": "0..1",
  "decision_threshold": "frozen value",
  "model_sha256": "frozen model hash",
  "policy_version": "local service policy id",
  "endpoint_to_gateway_latency_ms": "measured local-link latency",
  "gateway_decision_latency_ms": "measured gateway processing latency",
  "local_loop_latency_ms": "acquisition through endpoint acknowledgement",
  "requested_action": "monitor, reacquire, buffer_segment, or request_review"
}
```

### Gateway-Local Service Orchestrator

- Validate event schema, sequence continuity, freshness, and idempotency key.
- Reject malformed, stale, duplicate, or hash-mismatched events with retained reason codes.
- Apply a versioned decision policy locally on the gateway.
- Persist the event, action, acknowledgement, and terminal status.
- Coordinate endpoint buffering/retry when the local link is unavailable.
- Queue optional remote-review requests without blocking local monitoring or reacquisition.
- Never convert an isolated model probability directly into a diagnosis.

### Feedback and Validation

- Return acknowledgement from the gateway to the acquisition endpoint for every accepted or rejected local event.
- Record whether the requested action was accepted, completed, rejected, timed out, retried, or failed because the endpoint buffer limit was exceeded.
- For poor signal quality, issue a local reacquisition request to the endpoint.
- For persistent risk events, create a remote-review request according to a frozen aggregation policy, while the local loop continues independently.
- Update operational policy only through an explicit versioned configuration change; do not retrain from service feedback automatically.
## 9. Experimental Program

### Experiment 0: Data Contract and Audit — COMPLETE

Objective: fix data roles, preprocessing, lead mapping, record grouping, and hashes before expanded training.

Success evidence:

- 226 records audited.
- 678 WFDB files hashed.
- All records locally readable.
- Training, external-test, and normal-evaluation roles explicitly separated.

### Experiment 1: Multi-Source Training Ablation - COMPLETE

Objective: determine whether added databases improve generalization under an identical model and protocol.

Conditions:

- `M0`: MIT-BIH only.
- `M1`: MIT-BIH + INCART.
- `M2`: MIT-BIH + INCART + LTDDB.

Primary input: one-channel waveform only. Causal pre-RR is a secondary ablation; post-RR is an offline upper comparison.

Protocol:

1. Freeze source-aware record groups before training.
2. Use five outer record-level development folds. Each fold must contain records from every available training source where feasible.
3. Keep MIT-BIH 201/202 together.
4. Use inner record groups for epoch selection, calibration, and threshold selection; never use an outer test record for these decisions.
5. Sample hierarchically: source, record, then class. Do not concatenate all beats and let LTDDB dominate.
6. Keep architecture, optimizer, epoch policy, augmentation, and threshold rule identical across M0/M1/M2.
7. Run three fixed seeds per condition.
8. Save per-record predictions, calibration traces, configuration, split manifest, and hashes.

Primary development selection rule:

- Require development PVC recall of at least 0.90 if feasible.
- Among feasible operating points, select the highest record-level macro PVC F1.
- If no operating point reaches 0.90 recall, select the highest recall and mark the target as unmet.
- Prefer a larger dataset only if the paired record-level evidence supports it; "more beats" is not itself success.

Outputs:

- `results/experiment1/splits.json`
- `results/experiment1/runs.csv`
- `results/experiment1/per_record_predictions/`
- `results/experiment1/summary.json`
- Candidate models and frozen manifests under `models/experiment1/`

### Experiment 2: One- Versus Two-Channel Ablation - COMPLETE

Objective: determine whether a second synchronized channel justifies its hardware and compute cost.

Conditions:

- `L1`: `(300, 1)` input using the selected training-source condition.
- `L2`: `(300, 2)` input using the same split, seeds, calibration, and threshold protocol.

Compare:

- Record-level macro PVC F1, precision, recall, specificity, AUPRC, and Brier score.
- Parameter count, float model size, int8 model size, peak RAM, and p50/p95 inference latency.
- Per-source and worst-record behavior.

Decision rule: select L2 only if improvement is stable across seeds and records and its local-gateway compute cost plus endpoint acquisition and local-link bandwidth cost remain acceptable. Otherwise retain L1 as the primary system and report L2 as a negative or marginal result.

### Experiment 2.5: Pre-Freeze Model Optimization - COMPLETE

Objective: improve the selected M1/L2 development model to a preregistered, paper-relevant operating point before any final SVDB access, while preserving edge deployability, causal operation, record isolation, and transparent negative-result reporting.

Evidence classification:

- **Verified project evidence:** Experiment 2 completed L1/L2 with five outer folds and three seeds; L2 is development-preferred but is not frozen.
- **Verified literature evidence:** the focused sources listed below support morphology-plus-rhythm modeling, larger temporal receptive fields, compact edge inference, and explicit cross-database evaluation.
- **Targets:** all numerical success thresholds in this section are prospective optimization gates, not achieved findings.
- **Recommendations:** the candidate order and architecture budget are design decisions informed by the evidence; they are not literature-level novelty claims.

Data boundary:

- Use M1 development sources only: MIT-BIH plus INCART.
- Start from L2 `(300, 2)` as the software-frozen lead profile. Its simulated endpoint, local transport, and gateway-process resource behavior are evaluated in Experiments 7 and 8A; desktop measurements must be reported as software-runtime evidence, not physical device performance.
- Reuse the reviewed Experiment 1/2 record groups and split hash `fb003bbd3dc2e4d81f47df732032403a12bc9782a7f76042fdfd59fed346c787`.
- Do not enumerate, load, inspect, or derive any tuning information from SVDB or NSRDB.
- Do not use post-RR, whole-record future statistics, future beats, or target-record labels as model inputs.

Metric contract:

- **Support-aware record-macro PVC F1, precision, and recall:** average only over records containing at least one eligible `V` beat, because PVC F1 is mathematically undefined for a record with no positive PVC reference.
- **PVC-free records:** report false PVC decisions, specificity, false PVC detections per hour, and their record distribution separately.
- **Legacy continuity metric:** retain the existing all-record zero-filled macro PVC F1, where undefined record F1 values were recorded as zero. Never replace or hide this value.
- **Probability metrics:** report record-macro AUPRC on records containing both classes and record-macro Brier score on all eligible records.
- **Secondary metrics:** retain pooled precision, recall, F1, specificity, balanced accuracy, AUROC, AUPRC, and Brier score, but do not use pooled accuracy as the selection endpoint.

Prospective optimization targets:

| Metric | Required target |
|---|---:|
| Support-aware record-macro PVC F1 | >= 0.80 |
| Support-aware record-macro PVC recall | >= 0.90 |
| Support-aware record-macro PVC precision | >= 0.75 |
| Record-macro AUPRC | >= 0.88 |
| Record-macro Brier score | <= 0.04 |
| Legacy all-record zero-filled macro PVC F1 | >= 0.70 |
| Three-seed F1 standard deviation | <= 0.04 |
| Paired record-bootstrap F1 difference versus O0 | 95% CI lower bound > 0 |
| PVC-free-record false-positive burden | No increase; preferred reduction >= 25% |
| Full-integer int8 software artifact size | < 1 MiB before Gate S |
| Float/int8 decision agreement | >= 99% before Gate S |
| Software-gateway p95 neural inference | < 50 ms at Experiment 7, with host/runtime configuration declared |

Candidate ladder:

- `O0`: corrected-protocol L2 waveform baseline. Reproduce L2 under the Experiment 2.5 epoch-selection, calibration, metric, and artifact rules.
- `O1`: `O0` plus a strictly causal RR branch.
- `O2`: compact multi-scale residual temporal network plus the causal RR branch.
- `O3`: `O2` plus mild training-only robustness augmentation.

Causal RR branch for `O1` and later candidates:

- `pre_rr_seconds`: interval from the previous detected/reference R peak to the current R peak.
- `pre_rr_over_past8_median`: current pre-RR divided by the median of up to eight previously completed RR intervals.
- `pre_rr_over_previous_rr`: current pre-RR divided by the immediately preceding completed RR interval.
- `history_validity`: explicit validity indicators where the available causal history is shorter than requested.
- Fuse the RR vector through an approximately eight-unit MLP after waveform pooling. No feature may depend on the next R peak or a statistic computed from the complete record.

Compact morphology network for `O2`:

- Stem: `Conv1D`, 16 channels, kernel size 7.
- Four depthwise-separable residual temporal blocks with kernel size 9 and dilation rates `1, 2, 4, 8`.
- Use 24 to 32 channels, quantization-compatible activations, and foldable normalization.
- Concatenate global-average and global-max pooled morphology features with the causal RR branch, followed by a 32-unit dense classifier head.
- Target an effective temporal receptive field of at least 127 samples, approximately 353 ms at 360 Hz.
- Hard architecture cap: fewer than 100,000 trainable parameters before any pruning.
- Do not add a Transformer, LSTM, model ensemble, GAN, SMOTE, or a separate derivative branch in the primary ladder.

Training-only robustness for `O3`:

- Apply perturbations only to training windows and record every random seed and generation parameter.
- Candidate perturbations are R-center jitter up to 50 ms, mild baseline wander, weak 50/60 Hz interference, 25-35 dB muscle/noise contamination, and low-probability single-lead dropout.
- Preserve the clean development folds as the selection evidence.
- Experiment 6 must use separately frozen seeds and the declared 20, 10, and 5 dB severity grid; report that the final model was augmentation-trained rather than presenting those noise families as wholly unseen.

Nested protocol:

1. Preserve the five outer record folds and three fixed seeds `20260803`, `20260804`, and `20260805`.
2. Preserve hierarchical source -> record -> class sampling and prevent a source or long record from dominating.
3. Set a maximum of 20-30 epochs before execution and save per-epoch inner-fold curves.
4. Select epoch count only from inner record groups; use the median best epoch across the inner folds for the corresponding outer-fold final fit.
5. Keep optimizer, batch policy, and training budget identical across candidates unless the differing component is the declared ablation.
6. Fit Platt calibration on inner out-of-fold predictions with record/source-balanced weights so that each record and source has controlled aggregate influence.
7. Select one global threshold from inner data only. A feasible threshold must reach both pooled PVC recall >= 0.90 and support-aware record-macro recall >= 0.90.
8. Among feasible thresholds, maximize support-aware record-macro PVC F1; break ties by lower false-positive burden on PVC-free development records.
9. If no threshold is feasible, select the highest support-aware recall and mark the recall target unmet.
10. Save raw and calibrated probabilities, calibration coefficients, threshold traces, per-record metrics, learning curves, configurations, seeds, code hashes, and dependency versions.

Staged execution and stopping rule:

1. **Stage A screening:** run all `O0-O3` candidates on all five folds with the canonical screening seed `20260803`.
2. A candidate advances if it either satisfies every model-quality target or improves support-aware macro F1 by at least 0.02 versus `O0`, loses no more than 0.01 recall, reduces neither source-specific macro F1 by more than 0.01, and passes the software architecture cap. The Stage A `resource_screen_pass` field is only a parameter-count proxy; it is not evidence of int8 conversion or the Experiment 7 software-runtime benchmark.
3. **Stage B confirmation:** advancing candidates run the remaining two fixed seeds, yielding five folds by three seeds for every confirmed candidate.
4. Select by the mean across all three seeds and paired per-record evidence. Do not select the best seed.
5. The primary ladder stops after `O3`. If no candidate passes, exactly one preregistered backup is permitted: a training-only source/record-adversarial representation head with no added inference branch.
6. If the backup also fails, record the targets as unmet. Gate B must then contain an explicit proceed/stop decision; do not continue unconstrained architecture search.

Post-selection requirements:

- Complete the one bounded Experiment 2.6 refinement before Gate S; no further model search is permitted after it.
- Revalidate M0/M1/M2 and L1/L2 under the winning architecture and training protocol before claiming that the software-frozen model, rather than the historical baseline, supports those selections.
- Train one canonical final model on all M1 development records with the preregistered seed `20260803` and the median inner-selected epoch count. Fit Platt calibration and one global threshold only from its five-fold development OOF predictions.
- Export full-integer int8 TFLite from development-only representative samples, verify float/int8 agreement, and save weights, calibration parameters, threshold, dependency versions, code hashes, and model hashes under Gate S.
- Freeze one software architecture, source condition, lead profile, seed policy, calibration method, threshold, int8 artifact, and manifest before Experiment 3. Software gateway and simulated transport evidence are evaluated in Experiments 7 and 8A under Gate V.

Planned outputs:

- `results/experiment2_5/protocol.json`
- `results/experiment2_5/runs.csv`
- `results/experiment2_5/summary.json`
- `results/experiment2_5/calibration_traces/`
- `results/experiment2_5/learning_curves/`
- `results/experiment2_5/per_record_predictions/`
- Candidate exports and manifests under `models/experiment2_5/`

Focused evidence basis and comparability limits:

- de Chazal et al. (2004), DOI <https://doi.org/10.1109/TBME.2004.827359>: independent MIT-BIH record sets; morphology plus heartbeat/RR intervals; VEB sensitivity 77.7% and positive predictivity 81.9%.
- Llamedo et al. (2012), DOI <https://doi.org/10.1109/TITB.2012.2193408>: multilead morphology plus RR features with cross-database corroboration; approximately 90% ventricular sensitivity and positive predictivity, but with up to 12 leads.
- Zhang et al. (2021), DOI <https://doi.org/10.1155/2021/9946596>: inter-patient adversarial CNN plus RR features; strong VEB results on MIT-BIH, but not frozen cross-database evidence.
- Cai et al. (2022), DOI <https://doi.org/10.3390/bios12040185>: MIT-BIH training and INCART testing with automatic R peaks, signal-quality filtering, morphology templates, and rhythm rules; target-record template adaptation makes it non-equivalent to a frozen beat classifier.
- Ivora et al. (2022), DOI <https://doi.org/10.1038/s41598-022-16517-4>: joint automatic QRS detection/classification; external-database classification macro F1 around 0.73, illustrating the operational gap.
- Farag (2023), DOI <https://doi.org/10.3390/s23031365>: tiny inter-patient matched-filter CNN; cross-dataset macro F1 81.24% on INCART, model size about 15 KB, and sub-millisecond mean inference on the declared edge board.
- Rahman et al. (2023), DOI <https://doi.org/10.3390/s23115237>: systematic ECG augmentation survey supporting carefully bounded noise, baseline-wander, powerline, shift, and lead-dropout augmentation while warning that harmful transformations require empirical validation.
- Lim et al. (2024), DOI <https://doi.org/10.1016/j.compbiomed.2024.109062>: adaptive segmentation and relative heart-rate context improve premature-beat recognition; this project adapts the idea to past-only causal RR features.
- Huang et al. (2026), DOI <https://doi.org/10.3389/fphys.2026.1800941>: hierarchical multi-scale residual modeling supports the receptive-field hypothesis, but its approximately 19.1 million parameters and non-inter-patient protocol make its reported F1 values non-comparable to this project.

### Experiment 2.6: Controlled Core-Metric Refinement

Objective: conduct exactly one bounded, development-only refinement after Experiment 2.5 and before Gate S. It may improve support-aware PVC F1, recall, precision, AUPRC, Brier score, PVC-free false-positive burden, and three-seed stability without expanding the model beyond edge suitability.

Data and leakage boundary:

- Use MIT-BIH plus INCART only, the reviewed record groups, and split hash `fb003bbd3dc2e4d81f47df732032403a12bc9782a7f76042fdfd59fed346c787`.
- Do not enumerate, load, inspect, or derive any tuning information from SVDB or NSRDB.
- Preserve causal operation: no post-RR, future R peaks, whole-record future statistics, or target-record labels as inputs.
- Preserve five outer record folds, linked MIT-BIH 201/202 grouping, source -> record -> class sampling, inner-only epoch selection, calibration, and threshold selection.

Preregistered candidate set:

- `P0`: exact O1 reproduction control.
- `P1`: O1 with robust Platt-calibration and threshold selection from inner OOF predictions.
- `P2`: O1 with bounded causal RR feature clipping and validity-aware normalization.
- `P3`: O1 with fixed mild positive-class loss weighting and RR-branch regularization.
- Do not add a Transformer, LSTM, ensemble, GAN, SMOTE, future-context feature, or unbounded architecture search. Do not expand O3 augmentation severity.

Execution and selection:

1. Stage A runs P0-P3 on all five folds with seed `20260803`.
2. Stage B runs advancing candidates on seeds `20260803`, `20260804`, and `20260805`.
3. A candidate must not increase PVC-free-record false positives over O1, must retain mean support-aware recall >= 0.90, Brier deterioration <= 0.005, three-seed F1 standard deviation <= 0.04, and fewer than 100,000 parameters.
4. Prefer a candidate with three-seed minimum support-aware recall >= 0.90 when feasible. Then rank by paired record-bootstrap F1 versus O1, mean support-aware F1, AUPRC, lower Brier, lower PVC-free burden, and lower parameter count.
5. Claim an F1 improvement only if the 95% paired-bootstrap lower bound exceeds zero. A stability-only candidate may be retained only with F1 non-inferiority lower bound >= -0.01, no PVC-free false-positive increase, and the improved minimum-seed recall.
6. If no candidate is superior under this lexicographic rule, retain O1. The ladder stops after P3; no backup candidate is permitted without an explicit charter revision.

Outputs:

- `results/experiment2_6/protocol.json`
- `results/experiment2_6/runs.csv`
- `results/experiment2_6/summary.json`
- `results/experiment2_6/per_record_predictions/`
- `results/experiment2_6/learning_curves/`
- `models/experiment2_6/`

### Experiment 2.6R: Recall-Stability Protocol Revision

Objective: conduct one explicitly approved, small-scale, development-only protocol revision after Experiment 2.6 and before Gate S. Its primary objective is to improve the minimum of the three seed-level mean support-aware PVC recalls from P0's observed `0.8799` to at least `0.90`; it is not an unconstrained search for a higher mean F1. P0/O1 remains the control and is retained if no R candidate passes every gate.

Evidence and deviation disclosure:

- The immutable Experiment 2.6 artifacts remain the P0 control and must not be overwritten, regenerated, or selected against by best seed.
- R1-R3 use only MIT-BIH plus INCART, the reviewed record groups, split hash `fb003bbd3dc2e4d81f47df732032403a12bc9782a7f76042fdfd59fed346c787`, L2 `(300, 2)` input, causal RR inputs, source -> record -> class sampling, and the fixed seeds `20260803`, `20260804`, and `20260805`.
- SVDB and NSRDB must not be enumerated, loaded, inspected, or used by any 2.6R candidate, calibration, threshold, or selection code path. Before this protocol was registered, the Experiment 0 audit contract was read in full to satisfy the contributor-read requirement and exposed its pre-existing external-database metadata. No waveform, annotation, model, metric, threshold, or candidate information was derived from that exposure. It is an explicitly disclosed read-scope deviation and is not evidence or an input to 2.6R.
- VFDB and CUDB remain excluded because they do not provide reliable beat-level N/V labels for this task.

Preregistered candidate set:

- `R1`: exact P0/O1 architecture and training budget with a batch-level exponential moving average of trainable weights, decay `0.999`, initialized after the first update. Inner validation, epoch selection, final fit, and outer inference use the EMA weights. It adds no inference branch, parameter, or runtime cost.
- `R2`: exact P0/O1 architecture with fixed hard-PVC reweighting only. For each outer fold and seed, construct a four-way cross-fitted P0 proxy cache using only that outer fold's development records. Within each source, mark the bottom `25%` of true PVC beats ranked by their held-out raw P0 probability as hard. During candidate training, apply weight `1.15` only to those marked PVC beats; all other beats retain weight `1.0`. The outer test records are never scored or used to construct the cache.
- `R3`: exact P0/O1 model and P0's uncropped, source- and record-balanced Platt calibration with a `0.01` threshold grid. Unlike P1, which clipped logits and used a `0.02` global grid, R3 chooses only from thresholds that preserve at least `0.90` support-aware recall in every inner validation fold and do not increase the total PVC-free false decisions across those inner folds relative to P0's original aggregate selection. Among feasible thresholds, maximize the minimum inner-fold recall, then support-aware F1, then lower PVC-free burden. If no threshold is feasible, record R3 as infeasible; do not weaken either constraint.

Stage A and Stage B:

1. **Stage A screening:** run R1-R3, each on all five outer folds using only seed `20260803`; P0's existing five corresponding artifacts are read-only controls. The 15 primary R runs are separate from R2's retained development-only proxy-cache fits.
2. A candidate advances only if all five primary runs complete with valid provenance; aggregate PVC-free false decisions do not exceed P0's Stage A total of `161`; mean support-aware recall is at least `0.90`; mean support-aware F1 is no worse than P0 by `0.01`; mean record-macro AUPRC is no worse than P0 by `0.005`; mean record-macro Brier is no worse than P0 by `0.005`; and its model graph hash and parameter count equal P0's `3,506` parameters.
3. **Stage B confirmation:** only Stage A candidates run the remaining two seeds, producing five folds by three seeds. An advancing R2 repeats its cross-fitted cache independently for each seed. Never choose a best seed.
4. A candidate is accepted only if its minimum seed-level mean support-aware recall is at least `0.90`; its aggregate PVC-free false decisions across all 15 runs do not exceed P0's total of `330`; mean F1 is non-inferior to P0 by `0.01` with paired record-bootstrap lower bound at least `-0.01`; mean AUPRC is no worse than P0 by `0.005`; mean Brier is no worse than P0 by `0.005`; three-seed F1 standard deviation is at most `0.04`; and full-integer int8 conversion preflight succeeds from development-only representative data. An F1 improvement may be claimed only if the paired-bootstrap lower bound exceeds zero.
5. Rank accepted candidates by minimum seed-level recall, then paired F1 evidence, mean F1, AUPRC, lower Brier, lower PVC-free burden, and lower parameter count. If no candidate passes, retain P0/O1, record the negative result, and permanently stop model search before Gate S.

Outputs:

- `results/experiment2_6r/protocol.json`
- `results/experiment2_6r/runs.csv`
- `results/experiment2_6r/summary.json`
- `results/experiment2_6r/per_record_predictions/`
- `results/experiment2_6r/learning_curves/`
- `results/experiment2_6r/hard_pvc_proxy_cache/`
- `models/experiment2_6r/` only for a Stage B-accepted candidate's development-only int8 preflight
Stage A outcome — complete negative result:

- `R1` completed five folds with mean support-aware recall `0.8835`, mean F1 `0.7993`, and `303` PVC-free false decisions. It failed the recall, F1, AUPRC, Brier, and PVC-free safety gates.
- `R2` completed five folds with mean support-aware recall `0.9178`, mean F1 `0.8175`, mean AUPRC `0.9197`, mean Brier `0.0245`, and `161` PVC-free false decisions. It met the recall and safety gates but failed the preregistered F1 non-inferiority lower bound of `0.8206` versus P0's Stage A mean.
- `R3` completed five folds; its per-inner-fold safety threshold was infeasible in every fold, so it fell back to the P0 decision rule and reproduced P0's Stage A values: recall `0.9226`, F1 `0.8306`, AUPRC `0.9117`, Brier `0.0251`, and `161` PVC-free false decisions.
- No candidate entered Stage B. The three-seed minimum-recall objective was therefore not tested or achieved. Retain P0/O1 and permanently stop further model, sampling, calibration, and threshold optimization before the required M0/M1/M2 and L1/L2 revalidation.
### Gate S: Software Evaluation Freeze

Gate S occurs after Experiment 2.6 and final-architecture M0/M1/M2 and L1/L2 revalidation, before any final SVDB access. The selected candidate, or O1 if P0-P3 do not improve it, must be trained on all M1 development records with seed `20260803` and the median inner-selected epoch count. Its Platt calibration and global threshold must be fitted from five-fold OOF development predictions only.

Gate S requires a float Keras artifact, a full-integer int8 TFLite artifact, representative quantization samples from development data only, calibration parameters, threshold, model/code/split/dependency hashes, and an immutable manifest. Full-int8 size must be below 1 MiB; float/int8 decision agreement must be at least 99%, mean absolute calibrated-probability error at most 0.02, 99th-percentile absolute error at most 0.05, and support-aware F1 and recall loss at most 0.01 on the held development equivalence set. Software runtime, simulated transport, and process-memory values are measured later in Experiments 7 and 8A; no physical hardware inference follows.

### Experiment 3: Frozen SVDB Cross-Database Evaluation

Entry gate:

- Experiment 2.5 and the bounded Experiment 2.6 ladder are complete, with all unmet targets retained in the report.
- Gate S records the final development-only model-selection decision and the final-architecture M0/M1/M2 and L1/L2 revalidation status.
- Architecture, training sources, weights, seed policy, calibration, threshold, lead mapping, resampling, float artifact, int8 artifact, and manifest hashes are frozen.
- Physical endpoint, transport, and gateway hardware are not required for Gate S or Gate V and remain outside the current study scope.

SVDB must be evaluated without retraining, threshold changes, quantization changes, lead-profile changes, or selecting among seeds from SVDB performance.

Report:

- Pooled and record-level macro PVC precision, recall, F1, specificity, balanced accuracy, AUROC, AUPRC, and Brier score.
- Confusion matrix and per-record table.
- Record-level bootstrap 95% confidence intervals.
- Worst-decile records and error categories.

Because SVDB was used in prior exploratory work, describe it as an isolated cross-database holdout, not a pristine blind test.

### Experiment 4: NSRDB Normal-Rhythm False-Alarm Evaluation

NSRDB remains completely outside classifier fitting and threshold selection.

Report:

- False-positive rate on annotated `N` beats.
- False PVC detections per hour.
- False service escalations per hour after the frozen aggregation policy.
- Distribution across records and the worst record.
- Relationship between false alarms, signal quality, and R-peak errors.

Engineering target: no more than one false **service escalation** per hour under the frozen aggregation policy. Beat-level false positives remain descriptive and must not be hidden by aggregation.

### Experiment 5: Oracle Versus Automatic R-Peak Pipeline

Repeat the comparison using the final frozen model.

- Oracle path: reference annotation R peaks.
- Operational path: causal automatic R peaks.
- Fixed one-to-one match tolerance: 150 ms.
- Run on development sources, SVDB, and NSRDB without changing the classifier threshold.

Report:

- R-peak sensitivity, positive predictive value, F1, and localization error.
- PVC metrics for oracle and automatic paths.
- Absolute and relative classification degradation.
- Missed PVCs due to missed peaks, mislocalized peaks, and classifier errors.

### Experiment 6: Signal Robustness

Apply perturbations only after model freeze. Do not tune on SVDB perturbation results.

Conditions:

- Baseline wander.
- 50 Hz and 60 Hz interference.
- Band-limited muscle noise at 20, 10, and 5 dB SNR.
- Amplitude scaling from 0.5 to 2.0.
- Short sample loss and timing jitter.
- Lead dropout for the two-channel model.

Report degradation curves for R-peak F1, PVC F1, recall, false escalations per hour, and latency. Every synthetic perturbation must record its generation parameters and random seed.

### Experiment 7: Software Runtime and Local-Loop Benchmark

Experiment 7 is scheduled after Gate S, Experiments 3-6, and Experiment 8A. It measures the software runtime of the two logical tiers on a declared development host. The endpoint is a replay process, the local transport is a loopback MQTT v5 or deterministic in-process adapter, and the gateway is a local process. This is software-runtime evidence and is not a physical device benchmark.

Procedure:

1. Record the replay-endpoint identity, simulated transport profile, host OS/runtime, queue capacity, and logical clock method.
2. Verify the frozen full-integer int8 artifact, calibration, threshold, model hash, and policy version; do not refit them.
3. Warm up the gateway process and record the runtime version.
4. Run at least 1,000 inference windows and at least 30 complete simulated endpoint-to-gateway-to-endpoint sessions.
5. Measure p50, p95, p99, and maximum latency separately for simulated endpoint packetization, simulated local transport, mandatory post-R wait, gateway preprocessing/R-peak, neural inference, policy execution, and acknowledgement.
6. Measure model size, process peak resident memory, CPU load, message throughput, retries, sequence gaps, duplicates, and simulated buffer occupancy.
7. Repeat the same bounded loss, outage, duplicate, reorder, and restart conditions used in Experiment 8A.
8. Do not estimate energy or physical acquisition performance.

Targets:

- Int8 model size below 1 MiB.
- p95 software-gateway neural inference below 50 ms on the declared host/runtime.
- p95 simulated acquisition-to-local-decision latency below 600 ms, including the 416.7 ms post-R acquisition wait.
- Every accepted session has traceable endpoint, transport, gateway, model, policy, action, and acknowledgement provenance.
- All reported latency and resource values are labelled software-runtime measurements.

### Experiment 8A: Primary Software-Only Local Digital Service Loop and Fault Injection

Objective: validate the simulated endpoint-to-gateway message contract, local gateway inference and policy implementation, fault recovery, acknowledgement, and auditability. It runs an explicitly simulated replay endpoint, a local MQTT v5 loopback transport for the primary benchmark, deterministic in-process transport for unit tests, and a gateway process on the development computer. It must be labelled software-only simulated service-loop evidence and cannot support physical acquisition, hardware latency, energy, wearable, or deployment claims.

The minimum prototype below records the original design target. The completed 8A gateway actually forms the latest 300-sample packet window and uses a packet-local maximum-amplitude peak proxy; its `r_peak_source` metadata must not be cited as proof that the Experiment 5 causal detector ran in the MQTT loop. Section 13B registers the bounded attempt to close this evidence gap.

Minimum prototype:

- Explicitly labelled replay endpoint producer with timestamps, sequence numbers, bounded buffer, retransmission, and acknowledgement handling.
- Local MQTT v5 adapter using QoS 1 and idempotency keys; the broker and all critical-path services remain local without Internet dependency.
- Gateway service that validates schema, endpoint identity, freshness, sequence continuity, duplicates, model hash, and policy version.
- Causal stream reconstruction, signal-quality assessment, automatic R-peak interpretation, int8 inference, calibration, and threshold application.
- Versioned `policy-v1`: inadequate signal quality -> `reacquire`; below-threshold valid event -> `monitor`; one above-threshold event -> `buffer_segment`; at least three above-threshold events in 30 seconds -> non-diagnostic `request_review`; duplicates return the original acknowledgement without repeating an action.
- SQLite WAL inbox/outbox audit store with action states, acknowledgement states, and restart recovery. Retry at most three times with 100 ms, 500 ms, and 2 s delays before a retained `failed` terminal status.
- Optional remote-review egress isolated from the latency-critical local loop.

Fault scenarios:

- Duplicate and out-of-order events.
- Temporary local-link outage and endpoint-side buffering.
- 1%, 5%, and 10% packet loss or equivalent injected delivery failure.
- Sequence gaps, duplicates, endpoint buffer saturation, and stale retransmission.
- Delayed acknowledgement.
- Malformed event schema.
- Poor-signal event bursts.
- Model unavailable or hash mismatch.
- Gateway service restart with endpoint- and gateway-queued events.
- Internet outage while the local loop remains available.

Report:

- Endpoint-to-gateway-to-endpoint acknowledgement latency and its component breakdown.
- Successful terminal action rate.
- Duplicate-action rate.
- Event loss after reconnection.
- Recovery time.
- Local-link bandwidth and optional remote-egress bandwidth compared with continuous off-device raw ECG upload.
- Audit completeness: percentage of events with endpoint, transport, gateway, model, policy, action, acknowledgement, and terminal-status provenance.

Service targets:

- Zero duplicate actions under repeated event delivery.
- Zero permanent event loss after a bounded local-link outage and reconnection, within declared endpoint and gateway queue capacities.
- 100% audit-field completeness for accepted events.
- All rejected events retain a reason code.
- Safety fallback is local monitoring or reacquisition, never silent escalation failure.
- Internet loss does not prevent local monitoring, reacquisition, inference, policy execution, acknowledgement, or audit logging.
### Experiment 8B: Hardware Extension (Out of Scope)

Experiment 8B is not part of the advisor-approved software-only study and is not required for paper completion or Gate V. A future project may repeat the frozen Experiment 8A scenarios on declared ECG acquisition and gateway hardware, but those results must be registered separately and cannot be inferred from the current software evidence.

### Software-only execution order

`Experiment 2.5 -> Experiment 2.6 -> Gate S -> Experiment 3 -> Experiment 4 -> Experiment 5 -> Experiment 6 -> Experiment 8A -> Experiment 7 -> Gate V`

## 10. Statistical Analysis Plan

- Experiment 2.5 development primary metric: support-aware record-macro PVC F1 at the inner-selected operating point.
- A record contributes to support-aware PVC F1, precision, and recall only when it contains at least one eligible reference `V` beat; do not assign a zero F1 to a mathematically undefined case.
- Preserve and report the legacy all-record zero-filled macro PVC F1 alongside the support-aware metric for continuity with Experiments 1/2.
- For PVC-free records, report specificity, false PVC decisions, false PVC detections per hour, and eventually false service escalations per hour.
- Safety metrics: support-aware PVC recall and false service escalations per hour.
- Probability metrics: record-macro AUPRC and Brier score; AUROC is secondary because of class imbalance.
- Generalization metric: paired per-record difference between candidate models on identical folds.
- Analyze paired F1 differences on PVC-bearing records and false-positive burden separately on PVC-free records.
- Uncertainty: record-level bootstrap with at least 1,000 resamples and a fixed seed.
- Multi-seed reporting: mean, standard deviation, minimum, and maximum across three seeds.
- Do not treat beats from one record as independent participants.
- Do not report only pooled accuracy or pooled F1.
- Do not select a result by the best random seed.
- Disclose that the support-aware/zero-filled distinction was formalized after Experiment 2 but before the frozen external evaluation; never erase the original Experiment 1/2 summaries.
- Report unmet thresholds and negative ablations rather than modifying the protocol post hoc.
- Any new hypothesis after viewing SVDB is exploratory and must be tested on a different future dataset.

## 11. Model and Protocol Freeze Manifest

Before Experiment 3, create one immutable manifest containing:

- Training database names and record IDs.
- Record split groups and split hash.
- Lead profile and fallback records.
- Replay-fixture identity and explicit simulation status.
- Frozen simulated local transport profile, connection parameters, queue capacities, and logical clock method.
- Local gateway process, operating system, runtime, and host execution mode.
- Source and target sample rates.
- Window and normalization contract.
- Model architecture and parameter count.
- Training seeds and epoch policy.
- Calibration method and coefficients.
- PVC threshold and its selection rule.
- Model SHA-256.
- Dependency versions.
- Source-code commit hash or repository-state identifier.
- Date and operator.

If any field changes, issue a new manifest version. Do not overwrite the frozen version.

## 12. Paper Narrative

### Recommended Working Title

**An Accountable Two-Tier Edge Digital Service Loop for PVC Risk Escalation in Connected Healthcare**

### One-Sentence Positioning

This work studies whether an event-driven and auditable two-tier local-edge service loop, formed by a simulated ECG acquisition endpoint and local gateway process, can close sensing-to-feedback reliably without cloud-dependent inference; a frozen multi-source PVC model serves as its interpretation use case.

### Paper Structure

1. Connected-health fragmentation and the need for verifiable service loops.
2. Related work: ECG/PVC edge inference, connected-health orchestration, reliability, and provenance.
3. Proposed ECG acquisition-endpoint plus local-gateway architecture, versioned service contract, event schema, and governance boundary.
4. Event-driven orchestration, acknowledgement, audit, and recovery implementation.
5. Frozen multi-source PVC interpretation component, data roles, and leakage controls.
6. Service-loop, clinical, cross-database, resource, and fault-injection results.
7. Discussion: accuracy/latency/reliability trade-offs, limitations, and deployment implications.
8. Conclusion focused on measurable service behavior, not only classifier accuracy.

### Magazine Figure and Table Budget

Reserve **four figures and two tables** for the submitted article, with each item readable at magazine size. This is a ceiling and allocation, not a requirement to include an unsupported result. Detailed ablations, data contracts, and extra robustness plots remain in traceable supporting material instead of being squeezed into composite figures.

1. Figure 1: two-tier architecture and the sensing-to-acknowledgement service lifecycle, including local-only loop closure and optional remote review.
2. Figure 2: automatic-versus-reference R-peak consequences and the denominator-aware ECG-side error attribution; do not add service-event percentages to beat percentages.
3. Figure 3: bounded loss/outage/restart recovery and action/acknowledgement outcomes, labelled as synthetic fault injection.
4. Figure 4: Experiment 7 logical acquisition-to-decision latency components, separating the fixed 416.7 ms post-R window wait from software processing and transport; report the p95 total separately from additive mean stages.
5. Table 1: frozen interpretation component, data roles, and external/automatic-pipeline results with their distinct evaluation populations.
6. Table 2: service reliability, audit completeness, false escalation, software resource use, and claim boundaries; report record-level NSRDB limitations.

## 13. Literature Work Required Before Novelty Claims

Conduct a focused literature review in four streams:

1. Edge or TinyML ECG/PVC detection with cross-database validation.
2. Automatic R-peak plus downstream arrhythmia classification pipelines.
3. Two-tier edge/gateway digital service loops and event-driven local orchestration in connected healthcare.
4. Provenance, reliability, fault recovery, and human-in-the-loop escalation for medical IoT.

For each candidate paper, extract WHY, HOW, WHAT, data, hardware, loop stages implemented, metrics, and unresolved gaps. Record the read scope (full text, methods, or abstract only), DOI/source URL, and exactly which manuscript claim it supports. If only the abstract is available, mark unassessed methods as unassessed. Do not claim "first," "novel," or "state of the art" from a targeted search.

Start the targeted verification on **9 October 2026**, alongside rewriting the English introduction, related work, and architecture sections. Prioritize closest ECG service-loop or cloud-edge systems, MQTT ECG alert systems, signal-quality/false-alarm control, multi-database PVC classification, and fault-tolerant medical IoT. Check the existing matrix against primary sources, then add the missing service-level comparators. Select approximately 12-15 fully checked references for the submitted paper; the matrix may contain more screening candidates than the final reference list. Distinguish prior capabilities from this project's measured combination rather than stitching an untested feature into the claimed contribution.

## 13A. Post-Gate-V Convergence Protocol

Gate V is already passed. The remaining work strengthens and interprets the
evidence; it does not reopen Gate S2, the frozen external evaluations, or the
model/threshold/policy selection process.

### Real ECG Replay Strengthening Experiment

- Use fixed, locally available MIT-BIH and INCART fragments only; record IDs,
  fragment boundaries, channel mapping, source hashes, and replay seed must be
  written to a protocol before execution.
- Replay at least 10 fixed record fragments, at least 300 windows, and at least
  10 sessions through the existing simulated endpoint -> local MQTT v5 QoS 1 ->
  gateway path.
- Reuse the Gate S2 model hash, calibration, threshold `0.49`, L2 lead profile,
  `policy-v1`, service-contract version, and gateway runtime unchanged.
- Record window formation, automatic R-peak status, signal quality, requested
  action, ACK/terminal status, latency, and accepted/rejected audit completeness.
- Classify the result as post-Gate-V exploratory strengthening evidence. It may
  support a real-data replay claim, but it cannot modify Gate V or any frozen
  clinical/external result.
- The experiment must not be described as physical acquisition, hardware
  latency, energy, wearable, clinical-efficacy, or regulatory evidence.

### Cross-Layer Error Attribution

Create `results/cross_layer_attribution/` with a protocol, source-artifact
manifest, layer table, and figure. At minimum report:

- sensing: missed automatic R peaks and unmatched alarms;
- signal/window: window mislocalization and ineligible windows;
- interpretation: classifier or causal-RR errors;
- transport: loss, duplicate, reorder, outage, and recovery outcomes;
- orchestration: malformed/stale/hash-mismatch rejection and buffer saturation;
- feedback: ACK timeout/failure, restart recovery, and terminal-status outcomes.

Each layer must retain its own denominator, numerator, confidence or interval
method where applicable, and downstream impact. Do not sum percentages across
layers that represent different units. The paper may call this a
cross-layer error-attribution framework; the term `error budget` is reserved
for a future analysis with a defensible common denominator and aggregation rule.

### Evidence and Bandwidth Boundaries

- The current Experiment 8A baseline uses synthetic ECG samples for service
  fault testing. This fact must be stated wherever those results are used.
- The MQTT/JSON byte count is a protocol-overhead measurement. The current
  result is larger than a same-size two-channel 16-bit raw reference, so the
  paper must not claim bandwidth savings without a separately registered
  binary/compression comparison.
- Existing Gate V acceptance checks remain valid, but a real-ECG replay result
  is additive context and not a replacement for the registered Gate V artifact.

### Claim-to-Evidence Register

Until a new protocol explicitly supersedes it, the paper's service-loop claims
must use this exact frozen configuration:

| Item | Frozen value | Evidence |
|---|---|---|
| Model | Gate S2 M1/L2/P0/O1 full-int8; SHA-256 `edea13aacdd5f6f9f94a3b73092f567f25b4dcade6133da4af7eb42aa2913776` | `results/gate_s2_int8_tf215_run1/manifest.json` |
| Calibration/threshold | Fixed calibration; threshold `0.49` | `results/gate_s2_int8_tf215_run1/int8_direct_evaluation.json` |
| Policy | `policy-v1` | `src/service_loop/gateway_policy.py`, `docs/service-loop-governance.md` |
| Service contract | `ecg-service-contract-v1` | `src/service_loop/contracts.py` |
| Primary transport | Local MQTT v5 QoS 1 | `results/experiment7/protocol.json`, `results/experiment8a/protocol.json` |
| Gate V decision | Passed software-simulated validation | `results/gate_v/decision.json` |

Numerical claims about model quality, automatic R-peak degradation, runtime,
fault recovery, auditability, or bandwidth must link to a result artifact. A
literature claim must link to a verified source in the literature matrix. A
recommendation or hypothesis must be labelled as such and must not be written as
a finding.

## 13B. Time-Boxed Causal-Detector Service-Loop Bridge

The completed Experiment 8A and post-Gate-V replay used synthetic packet-centred
traffic and a packet-local peak proxy, respectively. Neither establishes that
the Experiment 5 causal detector drove the MQTT service loop. Register this
one bounded exploratory bridge before execution; it does not reopen Gate S2,
Gate V, the frozen external evaluations, or the model-selection process.

### Fixed Inputs and Configuration

- Reuse the ten named MIT-BIH/INCART record fragments, start samples, lead mappings, source hashes, and frozen record order from `results/experiment8a_real_replay/protocol.json`. These are development-source inputs for link-level validation, not a new external clinical test.
- Register `results/experiment8a_causal_bridge/protocol.json` before running. Record code commit or source hashes, packet/chunk size, clock method, fragment boundaries, detector state handling, expected output schema, and the fixed 150-sample post-R wait. Keep failed attempts and their reason codes.
- Reuse the Gate S2 int8 model hash, calibration, threshold `0.49`, L2 lead profile, `policy-v1`, `ecg-service-contract-v1`, and local MQTT v5 QoS 1. No source, model, detector, threshold, quality cutoff, policy, or seed may be chosen based on the bridge outcomes.
- Preserve chronological sample sequence through the simulated endpoint. Run the **unchanged Experiment 5 causal R-peak detector at the gateway** on the canonical two-channel replay, with detector state reset only at each fixed record boundary; form a 300-sample window only after its post-R samples are available, and carry the detected peak sample and emission sample into a companion event trace without changing the frozen service-event schema. If canonical resampling is done before MQTT transmission, label that preprocessing explicitly; do not claim a fully causal native-rate acquisition pipeline.
- A bounded adapter may retain the received sample prefix and call the existing detector on that prefix, emitting only newly available peaks whose `emitted_sample` is at or before the current prefix end. This keeps the detector implementation unchanged; record the repeated-computation cost separately and do not reuse Experiment 7 latency numbers as measurements of this adapter. Use the Experiment 5 causal RR feature and per-window normalization contracts, not the 8A packet-local proxy features.
- Use event identifiers tied to source record and detected peak. The local gateway must apply the frozen inference and policy, return an acknowledgement, and retain the event/action/terminal audit record. Do not count packet receipt as a completed service action.

### Measurements and Acceptance

- Save a per-event trace with record and source hashes, endpoint sample range, detected R-peak sample, peak emission sample, window eligibility, frozen model probability, signal quality, decision threshold, requested action, acknowledgement, terminal status, reason code, and audit identifier. Also save per-fragment counts of transmitted packets, detector peaks, eligible windows, accepted/rejected events, and missing acknowledgements.
- Compare the causal detector's peak locations on these same fixed fragments with the Experiment 5 implementation using the registered 150 ms match tolerance. Explain any mismatch before claiming a linked detector-to-service result. Report window-formation rate with its denominator and reason-coded exclusions.
- The bridge supports a linked software-replay claim only if every reported eligible event has traceable peak-to-action-to-terminal-ack lineage, accepted-event audit fields are complete, rejected attempts have reason codes, the frozen configuration hashes match, and no unresolved transport callback error remains. Report observed rates and failures even when these criteria fail. Do not infer a new clinical F1 from this development-only sample.
- Complete or close the attempt by **15 October 2026**. If incomplete or failed, retain the protocol and failure evidence, keep the Experiment 5 detector and existing packet-local-proxy replay as separate evidence, and remove wording that presents them as one validated automatic-detection service path. Do not extend the attempt by reopening frozen design choices.

### Channel-1-Loss Diagnostic

- In the same registered bridge, separately use fixed MIT-BIH `100` and INCART `I01` fragments. Inject one five-second channel-1 interruption from replay seconds 10 through 15 in each; retain channel 2, packet order, endpoint IDs, model, and policy unchanged. Record this fixed interval in the protocol before execution.
- Compare the clean and interrupted runs for packet acceptance, quality status, detected peaks, window formation, requested actions, reason codes, reacquire acknowledgements, and terminal audit entries.
- Determine whether the **existing** service path issues a reason-coded `reacquire` acknowledgement when no eligible detector event is formed. If it cannot, state this as an observed service limitation; do not create a new policy version or retrofit the frozen Gate V result to turn the diagnostic into a pass.

### Registered Outcome (9 October 2026)

`results/experiment8a_causal_bridge/protocol.json` was written before execution and records source/code hashes, all ten fixed fragments, the 180-sample MQTT chunk, the gateway prefix adapter, and the two fixed channel-1 interruptions. The unchanged detector formed 233 eligible service events from eight of ten clean fragments; all 233 had a frozen-model decision, local action, terminal MQTT ACK, and complete audit lineage. INCART I03 and I04 had zero detector peaks. Both channel-1 interruptions produced zero eligible events and zero reason-coded reacquire ACKs inside the gap. The bridge supports a narrow linked **software-replay** claim for events that formed, but the no-event reacquisition fallback failed this diagnostic. See `results/experiment8a_causal_bridge/report.md` for denominators and the pre-MQTT full-fragment resampling limit. Gate S2, Gate V, and frozen external results are unchanged.

## 14. Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| Multi-source training does not improve SVDB | High | Report negative result; choose development-selected model; retain service-loop contribution |
| LTDDB dominates due to long recordings | High | Hierarchical source/record/class sampling and per-source reporting |
| Two-channel semantics differ across databases | Medium | Fixed documented mappings; call it two-channel, not uniform lead-space fusion |
| Upsampling 128 Hz appears misleading | Medium | State that it standardizes timing and adds no physiological information |
| Automatic R-peak remains weak | High | Report the frozen Experiment 5 error decomposition and avoid post-freeze detector tuning |
| Centered window imposes 416.7 ms delay | Medium | Separate the fixed post-R wait from processing and transport latency; do not relabel model inference time as full-loop latency |
| No declared simulated endpoint, local transport, or gateway runtime in time | Critical | Freeze all three software profiles before Gate V; label replay endpoints and transport as simulated |
| Service prototype remains a message demo | High | Demonstrate endpoint buffering, local transport faults, gateway policy execution, acknowledgement, recovery, and audit metrics |
| Simulated endpoint and gateway clocks are not comparable | High | Freeze a logical clock or timestamp-correlation method and report its uncertainty |
| Cloud scope returns through implementation convenience | Medium | Keep cloud inference/orchestration outside the critical loop; isolate optional remote-review egress and test local operation during Internet outage |
| CFP mismatch from classifier-centric writing | Critical | Make service loop the title, architecture, evaluation unit, and discussion center |
| SVDB previously viewed | Medium | Disclose; freeze protocol and avoid "blind test" wording |
| Public databases do not establish clinical benefit | High | Limit claims to technical detection and service feasibility |
| Optimization overfits the reused development folds | High | Predeclare O0-O3, use one screening rule, confirm with all three seeds, allow only one backup, and rely on frozen SVDB for external evidence |
| Metric definition appears changed to improve scores | High | Report support-aware and legacy zero-filled macro F1 together; disclose the pre-external timing and evaluate PVC-free records with false-alarm metrics |
| Optimized architecture reverses M1 or L2 conclusions | High | Revalidate M0/M1/M2 and L1/L2 under the winning protocol before final selection claims |
| Synthetic 8A traffic is overinterpreted as real ECG service evidence | High | Run the fixed post-Gate-V real ECG replay strengthening experiment and label synthetic versus real replay results separately |
| Packet-local peak proxy is described as the Experiment 5 causal detector | Critical | Run the registered, time-boxed 8A causal bridge or explicitly keep their results separate in the paper |
| Channel-1 dropout silently prevents an eligible event and reacquisition | High | Run the fixed two-record dropout diagnostic; disclose a missing reason-coded ACK as a service limitation without changing frozen policy-v1 |
| Cross-layer failure rates are incorrectly added across incompatible units | High | Preserve layer-specific denominators and call the result error attribution, not an additive error budget |
| Protocol overhead is mistaken for bandwidth efficiency | Medium | Report JSON/MQTT bytes and raw-reference comparison as overhead; do not claim savings without a registered binary/compression study |
| New policy or interoperability work destabilizes the frozen study | High | Keep policy-v1, internal service contract, Gate V, and external results fixed; defer Evidence-Aware Policy and FHIR |
| Manuscript exceeds magazine format limits | High | Draft to at most 4,500 main-text words, six figures/tables combined, and 15 verified references; audit the limits before submission |
| Schedule compression | High | Use hard weekly gates and stop low-value architecture exploration |

## 15. Timeline to Submission

| Date | Gate | Required Deliverable |
|---|---|---|
| 2-3 Aug 2026 | Development evidence | Experiments 0-2 artifacts reviewed; M1 selected and L2 development-preferred pending software-loop evidence |
| 4-15 Aug | Experiment 2.5 optimization | O0-O3 Stage A, advancing-candidate Stage B, support-aware metrics, and int8 resource screening |
| 16-23 Aug | Final ablation validation | COMPLETE: P0/O1 M0/M1/M2 and L1/L2 revalidation; software endpoint/transport/gateway screen remains pending |
| 24-27 Aug | Model-selection gate | Experiment 2.5 decision, all unmet targets retained, final source/lead/seed policy selected |
| 28-31 Aug | Model freeze | COMPLETE: original Gate S attempts failed their immutable pointwise p99 criterion; the explicitly versioned Gate S2 deployment-probability amendment passed under TensorFlow 2.15.1. P0/O1/M1/L2 and the Gate S2 int8 artifact are software-frozen; external evaluation is unlocked. |
| 1-8 Sep | External evaluation | Experiments 3 (SVDB) and 4 (NSRDB) reports complete |
| 9-16 Sep | Operational ECG pipeline | COMPLETE: final automatic R-peak report and Experiment 6 robustness/fault-injection results |
| 17-27 Sep | Software runtime benchmark | Experiment 7 software gateway, simulated transport, latency, resource, and acknowledgement benchmark |
| 28 Sep-7 Oct | Software service loop | Experiment 8A orchestrator, acknowledgement, audit, recovery, and fault-injection results; Gate V evidence |
| 8-9 Oct | Existing convergence evidence | COMPLETE: real ECG packet-local-proxy replay, cross-layer attribution, claim-to-evidence boundary, and initial English draft exist |
| 9-11 Oct | Writing and literature start | Verify CFP/author limits and closest primary sources; map each contribution to evidence, set the six-item figure/table budget and 12-15-source shortlist, complete a detailed English outline, and start Introduction, Related Work, and Architecture revisions |
| 10-15 Oct | Bounded supporting experiment | COMPLETE 9 Oct: protocol was registered before the 8A causal bridge; the unchanged detector-to-MQTT trace and fixed two-record channel-1-loss diagnostic are in `results/experiment8a_causal_bridge/` |
| 15 Oct | Evidence/claim decision | RESOLVED EARLY 9 Oct: use only the linked-event software-replay claim for 233 formed baseline events from eight fragments; report two zero-event fragments and the missing reacquire ACK during both channel-1 interruptions. No model, detector, threshold, or policy search follows |
| 16-20 Oct | English first full version | Complete an accessible draft within 4,500 main-text words, using at most four figures, two tables, and 15 checked references; separate model, service, and software-runtime evidence |
| 21-28 Oct | Internal review and revision | Review methodology, source and numerical claims, manuscript integrity, CFP fit, format, and reproducibility; revise every unsupported claim and figure/table |
| 29-30 Oct | Submission freeze | No new exploratory experiments; confirm word/figure/reference counts, author and portal details, source links, declarations, and submission files |
| 31 Oct | Deadline | Submit through the IEEE Author Portal under the correct special-issue article type |

## 16. Decision Gates

### Gate A: Experimental Design Freeze

Must pass before Experiment 1:

- Exact record groups saved.
- Hierarchical sampling specified.
- All metrics and thresholds declared.
- Three seeds fixed.
- SVDB and NSRDB access prohibited from training code paths.

### Gate B: Model Selection

Use development evidence only. Do not inspect SVDB to choose M0/M1/M2, L1/L2, architecture, threshold, or seed.

- Execute the preregistered Experiment 2.5 ladder and stopping rule without adding undeclared candidates.
- Select candidates by three-seed means and paired record evidence, never by the best seed.
- Complete the final-architecture M0/M1/M2 and L1/L2 revalidation before claiming those choices apply to the final model.
- If Experiment 2.5 targets remain unmet after the one permitted backup, record an explicit proceed/stop rationale without weakening the targets.

### Gate C: External Test Unlock

Requires a completed Experiment 2.5 decision, a complete freeze manifest, and successful hash verification. External results are write-once evidence; subsequent changes create a new explicitly exploratory version.

### Gate D: CFP Alignment

The prototype must demonstrate every loop stage across the approved local architecture: sensing at the ECG acquisition endpoint; interpretation, decision, policy, and audit at the local gateway; execution and acknowledgement back to the endpoint; and outcome validation. Internet or cloud availability must not be required to close the loop. A model-only or gateway-only message demo fails this gate.

### Gate E: Manuscript Integrity

- Every numerical claim traces to an artifact.
- Every literature claim has a verified source.
- Simulated service behavior is labeled simulated.
- No clinical efficacy or regulatory claim exceeds the evidence.

### Gate V: Software Loop Validation

Gate V replaces the hardware-dependent Gate H for this research version. It
requires completed Experiment 8A and Experiment 7 artifacts using the same
frozen model, calibration, threshold, policy, event schema, simulated endpoint,
and local transport profile. No physical endpoint, gateway, energy meter, or
MCU is required.

Gate V passes only when:

- The simulated endpoint, local transport, and gateway process have explicit
  responsibilities and stable identifiers.
- Events carry endpoint identity, timestamps, monotonic sequence numbers,
  model hash, policy version, action, acknowledgement, and terminal status.
- Duplicate and out-of-order delivery is handled without duplicate service
  actions; bounded loss and outage recover without permanent event loss within
  declared queues.
- Gateway restart recovers queued events and SQLite WAL audit state.
- Accepted-event audit-field completeness is 100%, and every rejected event
  retains a reason code.
- The local loop continues without Internet or cloud availability.
- Latency, CPU, memory, throughput, and recovery values are reported as
  software-runtime measurements and all service behavior is labelled simulated.
- No conclusion claims physical ECG acquisition, hardware latency, energy,
  MCU suitability, or wearable deployment.

### Gate S2: Deployment-Probability Protocol Amendment (2026-08-08)

The original Gate S remains a completed negative result and is not reclassified. A
single, explicitly versioned Gate S2 amendment is permitted because the deployed
artifact is full-integer int8, while the original p99 criterion measures pointwise
agreement with a float reference that is not deployed. This amendment is informed
by Jacob et al. (CVPR 2018, DOI <https://doi.org/10.1109/CVPR.2018.00286>), which
defines integer-only inference as a distinct deployment computation, and Guo et al.
(ICML 2017, arXiv:1706.04599), which supports fitting a post-processing calibration
map on held-out predictions. Recent ECG edge studies likewise evaluate quantized
models directly on the target runtime (Hizem et al., 2025, DOI
<https://doi.org/10.3390/s25082496>), while warning that accuracy/resource trade-offs
must be measured together.

Gate S2 is a protocol amendment, not a pass of the original Gate S. It must:

- preserve P0/O1, M1 (MIT-BIH + INCART), L2, the reviewed record groups, causal inputs,
  seed `20260803`, and the frozen epoch policy;
- use only development records and five outer-fold int8 OOF predictions to fit one
  source/record-balanced Platt map and one global threshold for the deployed int8
  artifact; no equivalence-set labels may fit calibration or threshold;
- retain the original float/int8 decision agreement, mean error, and p99 error as
  descriptive paired diagnostics, with the p99 failure disclosed; these values must
  not be silently removed or renamed;
- accept only if the directly calibrated int8 OOF/development evidence satisfies
  support-aware PVC F1 >= 0.80, support-aware PVC recall >= 0.90, support-aware PVC
  precision >= 0.75, record-macro AUPRC >= 0.88, record-macro Brier <= 0.04, legacy
  zero-filled macro F1 >= 0.70, PVC-free false decisions no greater than the P0
  control, int8 size < 1 MiB, and float/int8 decision agreement >= 0.99 on the held
  development equivalence set;
- stop after this one fixed evaluation. It may not search calibration families,
  thresholds, representative sets, converters, architectures, weights, or seeds.

If Gate S2 fails, retain P0/O1 as a development model and keep SVDB/NSRDB locked.
Only a passed Gate S2 may unlock the existing external-evaluation queue, and the
paper must report both the original Gate S failure and the Gate S2 decision.

## 17. Immediate Execution Queue

1. **Complete:** Revalidate M0/M1/M2 and L1/L2 under the retained O1/P0 final protocol; evidence is in `results/final_revalidation/`.
2. Original Gate S conversion attempts and the one registered standard QAT remediation failed immutable equivalence criteria. Preserve those artifacts and do not alter their status.
3. **Complete: Gate S2 (one-time amendment).** The TensorFlow 2.16.1 execution aborted before metrics; the explicitly selected TensorFlow 2.15.1 rerun passed all registered Gate S2 criteria. The software-frozen artifacts are `models/gate_s2_int8_tf215_run1/` and `results/gate_s2_int8_tf215_run1/`. Do not run further model, calibration, threshold, representative-data, converter, or quantization searches.
4. **Complete: Experiment 3 frozen SVDB evaluation.** The passed Gate S2 full-int8 P0/O1/M1/L2 artifact, fixed Platt calibration, and threshold `0.49` were evaluated exactly once on all 78 SVDB records with oracle annotation windows. The result, per-record predictions, record-level bootstrap intervals, and integrity verification are in `results/experiment3/`. No retraining, calibration, threshold, quantization, lead-profile, preprocessing, seed, or model selection followed the result.
5. **Complete: Experiment 4 NSRDB false-alarm evaluation.** The same passed Gate S2 full-int8 P0/O1/M1/L2 artifact, fixed Platt calibration, and threshold `0.49` were evaluated exactly once on all 18 NSRDB records. Overall policy-v1 false service escalation was `0.606/h`, but the record-bootstrap upper confidence limit was `1.638/h` and the worst record was `9.0/h`; preserve this record-level limitation. The result and integrity verification are in `results/experiment4/`. No retraining, calibration, threshold, quantization, lead-profile, preprocessing, seed, or model selection followed the result.
6. **Complete: Experiment 5 automatic R-peak evaluation.** The frozen Gate S2 P0/O1/M1/L2 int8 artifact and threshold `0.49` were evaluated with the existing causal detector. The final report is `results/experiment5_retry2/`; no detector, model, calibration, threshold, preprocessing, lead, quantization, or seed selection followed.
7. **Complete: Experiment 6 robustness and fault injection.** Part 1 and Part 2 are verified in `results/experiment6_part1/` and `results/experiment6_part2/`; no model, detector, calibration, threshold, quantization, preprocessing, lead-profile, or seed selection followed.
8. **Complete: Experiment 8A.** The primary software-only local MQTT v5 loopback benchmark completed with the simulated replay endpoint and gateway process. Results are in `results/experiment8a/`; do not present them as physical deployment evidence.
9. **Complete: Experiment 7 and Gate V.** The matching software runtime benchmark is in `results/experiment7/`, and `results/gate_v/decision.json` records a passed Gate V. Do not create a hardware Gate H requirement.
10. **Complete:** post-Gate-V real ECG replay strengthening. Results are in `results/experiment8a_real_replay/`; the packet-local peak proxy limitation is recorded and no Gate V or external result changed.
11. **Complete:** cross-layer error-attribution synthesis. Results are in `results/cross_layer_attribution/`; incompatible denominators are not aggregated.
12. **Bilingual working drafts complete, 9 Oct:** targeted primary-source checks and claim boundaries are in `docs/literature-matrix.md`; English and Chinese working manuscripts are `manuscript/draft.md` and `manuscript/draft.zh-CN.md`. These are writing drafts, not submission-ready versions. Preserve the current `models/` contents as historical baselines.
13. **Continue 9-11 Oct:** use `docs/iotm-style-benchmark.md` for the official format and observed article-style constraints; audit all working references and metadata at their recorded read scope, and refine the contribution-to-evidence map and English wording. Four evidence-linked PDF/PNG figures are now in `manuscript/figures/`, generated by `scripts/build_manuscript_figures.py`; the drafts retain two tables, the registered bridge, and its no-event limitation. Figure 4 uses additive mean stages and separately marks the p95 total, so component p95 values are never summed.
14. **Complete 9 Oct:** the 8A causal-detector-to-MQTT bridge and fixed channel-1-loss diagnostic are registered and reported in `results/experiment8a_causal_bridge/`. Preserve their artifact hashes and do not silently substitute the packet-local proxy. The narrow linked-event claim passed; the no-event reacquire fallback did not.
15. **16-30 Oct:** complete the English first version, internal methodology/integrity/CFP review, revisions, and final format/package check according to Section 15. Recheck the NSRDB record-level false escalation limit, the 416.7 ms post-R wait, and the software-only deployment boundary.

## 18. Rules for Future Agents and Contributors

### Must

- Read this file and `results/experiment0/preprocessing_contract.json` before changing experiments.
- Preserve database roles and record-group isolation.
- Use `apply_patch` for manual source edits.
- Store configurations, per-record outputs, seeds, and hashes with every run.
- Distinguish verified evidence, inference, target, and recommendation.
- Update the status table and timeline when a gate is completed.
- Keep the service loop central to architecture and evaluation decisions.
- Preserve the advisor-approved logical acquisition-endpoint plus local-gateway partition and keep the latency-critical loop independent of cloud connectivity.
- Label replay-based acquisition, local transport, and gateway-process evidence as software simulation/runtime evidence; no physical acquisition interpretation is allowed.
- Treat the post-Gate-V real ECG replay as exploratory strengthening evidence; it must reuse the frozen model hash, threshold, policy, event schema, lead profile, and MQTT transport.
- For cross-layer analyses, report each layer's denominator and preserve the distinction between error attribution and an additive error budget.
- Keep claim-to-evidence links and literature verification current before using novelty language in the manuscript.
- Keep the 8A causal bridge exploratory and time-boxed; report a failed or incomplete bridge and the channel-1-loss outcome without altering Gate S2, Gate V, or the frozen model/policy.
- Enforce the magazine's 4,500-word main-text, six combined figure/table, and 15-reference limits during drafting and final review.

### Must Not

- Train on SVDB or NSRDB.
- Tune on final SVDB results.
- Randomly split beats across train and test.
- Count beats as independent patients.
- Report only accuracy or pooled metrics.
- Select the best seed after seeing external-test results.
- Present software-host runtime as physical device latency.
- Put cloud inference, cloud orchestration, or Internet availability on the latency-critical local-loop path.
- Claim physical acquisition latency, hardware energy, or wearable suitability from a software replay endpoint.
- Present synthetic fault injection as a clinical pilot.
- Claim compatibility with arbitrary sample rates or lead counts.
- Claim novelty before the literature audit.
- Present synthetic Experiment 8A traffic as real ECG deployment evidence.
- Present the packet-local peak proxy as the Experiment 5 causal detector or a failed bridge as a passed end-to-end automatic-detection result.
- Change the frozen policy, model, threshold, event schema, transport profile, or Gate V interpretation through a post-Gate-V exploratory analysis.
- Claim bandwidth savings from the current MQTT/JSON byte count.
- Add FHIR or a new policy version to the main evidence without a separately registered protocol and independent evaluation.
- Delete legacy result artifacts until replacement evidence is verified and archived.

## 19. Completion Definition

The existing evidence is sufficient to begin English manuscript writing now. Submission readiness requires all of the following:

- Experiment 2.5 is complete under its preregistered ladder, one-backup limit, and stopping rule.
- Final-architecture M0/M1/M2 and L1/L2 comparisons are complete.
- Support-aware and legacy zero-filled record-macro metrics are both preserved, with PVC-free records reported through false-alarm metrics.
- One model and threshold are frozen from development evidence only.
- SVDB and NSRDB evaluations are complete.
- Automatic R-peak and robustness analyses use the final model.
- The int8 model has been measured in the declared software gateway runtime, and the simulated acquisition endpoint plus local transport path are explicitly labelled as software simulation.
- The event-driven loop closes from the simulated ECG acquisition endpoint to the local gateway process and back to the endpoint with acknowledgement and auditable feedback while Internet connectivity is absent.
- Fault-injection metrics meet or transparently report the predefined targets.
- Gate V passes using the Experiment 7 software runtime and Experiment 8A software service-loop artifacts.
- The fixed post-Gate-V real ECG replay strengthening experiment is complete, with the packet-local peak proxy limitation reflected in the manuscript.
- The cross-layer error-attribution table and report preserve layer-specific denominators and source-artifact links.
- The time-boxed causal bridge and channel-1-loss diagnostic are completed or explicitly closed with failure evidence by 15 October; manuscript claims match the observed outcome.
- Verified primary sources support the final novelty wording and every reference and cited claim is checked at its actual read scope.
- Every result cited in the manuscript has a reproducible artifact path.
- The accessible manuscript stays within 4,500 main-text words, six figures/tables in total, and 15 references; internal methodology, integrity, CFP-scope, and reproducibility review is complete.

Until then, the project has a promising and well-audited software-simulated prototype, not a publication-ready physical healthcare deployment.


