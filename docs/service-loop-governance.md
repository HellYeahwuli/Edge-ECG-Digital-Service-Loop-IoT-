# Service-Loop Governance and Threat Boundary

This prototype is a software-simulated, non-diagnostic connected-health
service loop. Its purpose is to measure event orchestration, feedback,
recovery, provenance, and software-runtime behavior. It is not a medical
device, clinical decision system, or regulatory-compliance implementation.

## Contract and lifecycle

- Contract version: `ecg-service-contract-v1`.
- Policy version: `policy-v1`.
- The gateway accepts only the exact registered contract, model hash, policy
  version, endpoint/gateway identity, lead profile, and sample sequence.
- Every accepted event records packet, interpretation event, requested action,
  acknowledgement, and terminal outbox state.
- Every rejected attempt records a reason code, including malformed payloads.
- Operational changes require an explicit versioned configuration update; no
  online retraining or automatic policy mutation is allowed.

## Safe actions and validation

Allowed actions are `monitor`, `reacquire`, `buffer_segment`, and the
non-diagnostic `request_review`. Poor signal quality produces `reacquire`.
Repeated delivery is idempotent and returns the stored acknowledgement without
repeating the action. Endpoint and gateway queues are bounded; overflow and
failed terminal delivery remain visible in the audit record.

## Threat boundary

Experiment 8A checks malformed messages, stale/incorrect sequence state,
contract/policy/model mismatches, packet loss, reordering, duplicate delivery,
local-link outage, delayed acknowledgement, bounded-buffer saturation, and
gateway restart. Internet availability is outside the latency-critical local
path. The loopback broker uses anonymous access only because it is isolated to
`127.0.0.1` for controlled simulation; it is not a secure deployment profile.

The prototype does not implement patient identity, clinical records, FHIR,
transport authentication, encryption key management, authorization, consent,
multi-tenant isolation, or regulatory reporting. Those capabilities are future
deployment requirements and must not be inferred from Gate V.

## Privacy and claim limits

Public ECG datasets are replayed under pseudonymous endpoint identifiers. No
new participant data are collected, and the benchmark does not transmit data
to Internet services. Results may support claims about a measurable simulated
service loop, but not physical acquisition, hardware latency, energy,
wearability, clinical efficacy, patient outcomes, regulatory approval, or
production security.
