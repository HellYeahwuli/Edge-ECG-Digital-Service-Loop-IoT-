# Experiment Matrix

| Experiment | Status in release | Role |
|---|---|---|
| 0 | Complete | Data and preprocessing audit |
| 1 | Complete | Multi-source development training |
| 2 | Complete | One- versus two-channel development comparison |
| 2.5/2.6/2.6R | Complete | Bounded development optimization and stopping rule |
| Final revalidation | Complete | M0/M1/M2 and L1/L2 revalidation |
| Gate S | Failed original criterion | Negative quantization/equivalence evidence retained |
| Gate S2 | Passed | Direct int8 calibration amendment |
| 3 | Complete | Frozen SVDB evaluation |
| 4 | Complete | Frozen NSRDB false-alarm evaluation |
| 5 | Complete | Reference versus automatic R-peak evaluation |
| 6 | Complete | Frozen-model robustness and fault injection |
| 7 | Complete; MQTT v5 loopback | 1,020-window, 30-session software runtime and local-loop benchmark; no hardware claim |
| 8A | Complete; MQTT v5 loopback | Primary software-only local orchestration and fault-injection benchmark |
| 8B / Gate H | Not applicable | Hardware extension outside the advisor-approved software-only scope |
| Gate V | Passed | Matching MQTT Experiment 7 and 8A artifacts; software-simulated service-loop claim only |

External test data were not used for architecture, threshold, calibration,
lead-profile, seed, or quantization selection.
