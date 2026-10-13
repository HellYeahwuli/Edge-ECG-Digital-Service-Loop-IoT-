"""Simulated acquisition endpoint with bounded local retransmission buffer."""

from __future__ import annotations

from collections import OrderedDict
from uuid import uuid4

from .contracts import Acknowledgement, ECGPacket, utc_now


class ReplayEndpoint:
    def __init__(self, endpoint_id: str, gateway_id: str, lead_profile: str, sample_rate_hz: float, model_sha256: str, policy_version: str, buffer_capacity: int = 128) -> None:
        self.endpoint_id, self.gateway_id = endpoint_id, gateway_id
        self.lead_profile, self.sample_rate_hz = lead_profile, sample_rate_hz
        self.model_sha256, self.policy_version = model_sha256, policy_version
        self.buffer_capacity = buffer_capacity
        self.sequence = 0
        self.buffer: OrderedDict[str, ECGPacket] = OrderedDict()
        self.acks: dict[str, Acknowledgement] = {}
        self.buffer_overflow_count = 0
        self.generated_packet_count = 0
        self.generated_sample_count = 0

    def packet(self, samples: list[list[float]], event_id: str | None = None) -> ECGPacket:
        event_id = event_id or str(uuid4())
        packet = ECGPacket(event_id, self.endpoint_id, self.gateway_id, self.sequence, utc_now(), self.lead_profile, self.sample_rate_hz, "local_mqtt_v5_qos1", self.model_sha256, self.policy_version, samples)
        self.sequence += len(samples)
        self.buffer[event_id] = packet
        self.generated_packet_count += 1
        self.generated_sample_count += len(samples)
        while len(self.buffer) > self.buffer_capacity:
            self.buffer.popitem(last=False)
            self.buffer_overflow_count += 1
        return packet

    def receive_ack(self, payload: dict) -> None:
        ack = Acknowledgement(**payload)
        self.acks[ack.event_id] = ack
        # Sequence-gap acknowledgements are retryable; retain those packets so
        # ordered retransmission can succeed after the missing predecessor.
        if ack.terminal_status != "retryable":
            self.buffer.pop(ack.event_id, None)

    def retransmit(self) -> list[ECGPacket]:
        return list(self.buffer.values())
