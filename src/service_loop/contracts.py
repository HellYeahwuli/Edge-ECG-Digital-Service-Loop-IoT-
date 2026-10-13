"""Hardware- and transport-independent service-loop event contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

import math
import time


SERVICE_CONTRACT_VERSION = "ecg-service-contract-v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _required(payload: dict[str, Any], names: tuple[str, ...]) -> None:
    missing = [name for name in names if payload.get(name) in (None, "")]
    if missing:
        raise ValueError("malformed_schema: missing " + ", ".join(missing))


@dataclass(frozen=True)
class ECGPacket:
    event_id: str
    endpoint_id: str
    gateway_id: str
    sample_sequence: int
    recorded_at: str
    lead_profile: str
    native_sample_rate_hz: float
    transport_profile: str
    model_sha256: str
    policy_version: str
    samples: list[list[float]]
    simulated_acquisition_endpoint: bool = True
    packetized_at_monotonic_ns: int = field(default_factory=time.perf_counter_ns)
    contract_version: str = SERVICE_CONTRACT_VERSION

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ECGPacket":
        if not isinstance(payload, dict):
            raise ValueError("malformed_schema: payload must be an object")
        _required(payload, ("event_id", "endpoint_id", "gateway_id", "recorded_at", "lead_profile", "transport_profile", "model_sha256", "policy_version", "contract_version", "samples"))
        if not isinstance(payload["sample_sequence"], int) or payload["sample_sequence"] < 0:
            raise ValueError("malformed_schema: sample_sequence")
        if payload["lead_profile"] not in {"one_channel", "two_channel"}:
            raise ValueError("malformed_schema: lead_profile")
        try:
            sample_rate = float(payload["native_sample_rate_hz"])
        except (TypeError, ValueError) as error:
            raise ValueError("malformed_schema: native_sample_rate_hz") from error
        if not math.isfinite(sample_rate) or sample_rate <= 0 or not isinstance(payload["samples"], list) or not payload["samples"]:
            raise ValueError("malformed_schema: samples")
        try:
            return cls(**payload)
        except (TypeError, ValueError) as error:
            raise ValueError(f"malformed_schema: {error}") from error

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GatewayEvent:
    event_id: str
    endpoint_id: str
    gateway_id: str
    sample_sequence: int
    recorded_at: str
    lead_profile: str
    native_sample_rate_hz: float
    transport_profile: str
    model_sha256: str
    policy_version: str
    signal_quality: float
    pvc_probability: float
    decision_threshold: float
    r_peak_source: str = "automatic"
    simulated_acquisition_endpoint: bool = True
    contract_version: str = SERVICE_CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ActionRecord:
    event_id: str
    endpoint_id: str
    gateway_id: str
    policy_version: str
    requested_action: str
    status: str
    reason: str
    created_at: str
    contract_version: str = SERVICE_CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Acknowledgement:
    event_id: str
    endpoint_id: str
    gateway_id: str
    ack_status: str
    requested_action: str
    reason: str
    policy_version: str
    acknowledged_at: str
    terminal_status: str = "completed"
    contract_version: str = SERVICE_CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
