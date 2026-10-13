# Two-Tier Architecture

```text
Simulated ECG acquisition endpoint
  replay, timestamps, sequence numbers, bounded software buffer
        |
        | frozen local transport profile
        v
Local gateway process
  stream reconstruction, quality, resampling, causal R-peaks,
  int8 inference, policy, audit, acknowledgement
        |
        v
Endpoint acknowledgement and reacquisition command
```

The latency-critical loop is local and must not require Internet or cloud
inference. The replay endpoint, local transport, and gateway process are
deliberately labelled software simulation/runtime components. They provide
contract, fault-injection, and software-resource evidence, not physical
acquisition or hardware performance evidence.

The study validates a software-simulated two-tier local-edge service loop
consisting of a replay-based ECG acquisition endpoint and a local gateway
process. The results do not establish physical ECG acquisition, hardware
latency, energy consumption, or wearable deployment suitability.

The gateway policy is non-diagnostic. It can continue monitoring, request
reacquisition, buffer a segment, or request human review after the frozen
multi-event policy is satisfied.

The wire contract is versioned as `ecg-service-contract-v1`. Exact contract,
model-hash, and policy-version agreement is required; mismatches and malformed
payloads are rejected with persisted reason codes. A single-host monotonic
clock (`time.perf_counter_ns`) supports software latency decomposition while
UTC timestamps support retained audit records. See
[service-loop governance](service-loop-governance.md) for the privacy,
security, lifecycle, and claim boundary.
