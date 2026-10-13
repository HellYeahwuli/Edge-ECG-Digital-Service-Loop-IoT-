# Reproducibility Guide

This release separates lightweight public code and evidence from local data
and large experiment artifacts.

## Smoke Checks Without ECG Data

```powershell
$env:PYTHONPATH = "$PWD/src"
python -m unittest discover -s tests -v
python -m compileall src tests
python -m service_loop.run_demo
```

The demo is a contract and idempotency demonstration. It is not an Experiment
8A benchmark and does not measure physical acquisition, energy, transport, or
gateway latency.

## Frozen Software Configuration

The Gate S2 artifact was evaluated with Python 3.10 and TensorFlow 2.15.1.
Install `requirements-gate-s2.txt` for that runtime family. The frozen
development configuration is M1 (MIT-BIH + INCART), L2 (two fixed channels),
candidate P0/O1, seed `20260803`, canonical rate 360 Hz, 300-sample windows,
and threshold `0.49`. Calibration and threshold selection use development
records only.

The exact model and artifact hashes are published in
`results_public/software_freeze_manifest.json`. The full model, calibration
traces, per-record predictions, and raw data remain outside GitHub.

## Evidence Boundaries

The original Gate S pointwise-equivalence attempt failed its p99 criterion and
is retained as a negative result. Gate S2 passed its registered direct-int8
criteria under TensorFlow 2.15.1. SVDB and NSRDB were evaluated after the
software freeze, but the SVDB run is described as an isolated cross-database
holdout rather than a pristine blind test.

Experiment 6, software-only Experiment 8A, software runtime Experiment 7, and
Gate V are complete. The post-Gate-V real ECG replay and causal-detector bridge
are exploratory; the bridge produced no eligible events on two fragments and
did not demonstrate a no-event reacquisition fallback during channel-1 loss.
Experiment 8B and Gate H are outside the advisor-approved software-only scope.
No physical two-tier
deployment, energy result, clinical efficacy, or regulatory claim may be
inferred from the current software-simulated service-loop package.

The study validates a software-simulated two-tier local-edge service loop
consisting of a replay-based ECG acquisition endpoint and a local gateway
process. The results do not establish physical ECG acquisition, hardware
latency, energy consumption, or wearable deployment suitability.

## Service-Loop Execution

Use the TensorFlow 2.15.1 environment and a loopback-only MQTT v5 broker:

```powershell
conda install -n edge-ecg-tf215 -c conda-forge paho-mqtt mosquitto -y
& .\scripts\run_service_loop_experiments.ps1 -EnvironmentPath "<path-to-edge-ecg-tf215>"
```

The broker configuration listens only on `127.0.0.1:1883`. Anonymous access is
permitted solely for the isolated software simulation and is not a production
security profile. The in-memory transport can be used for preflight checks but
cannot satisfy the primary MQTT criterion in Gate V.
