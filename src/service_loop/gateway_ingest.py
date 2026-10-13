"""Gateway schema, provenance, freshness, sequence, and idempotency checks."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from .contracts import Acknowledgement, ECGPacket, SERVICE_CONTRACT_VERSION, utc_now


class GatewayIngest:
    RETRYABLE_REASONS = {"sequence_gap"}

    def __init__(self, gateway_id: str, model_sha256: str, policy_version: str, store, policy, stale_after_seconds: float = 10.0, contract_version: str = SERVICE_CONTRACT_VERSION) -> None:
        self.gateway_id = gateway_id
        self.model_sha256 = model_sha256
        self.policy_version = policy_version
        self.store = store
        self.policy = policy
        self.stale_after_seconds = stale_after_seconds
        self.contract_version = contract_version
        self.next_sequence: dict[str, int] = store.next_sequence_map()

    def _ack(self, packet: ECGPacket, status: str, action: str, reason: str) -> Acknowledgement:
        terminal = "retryable" if reason in self.RETRYABLE_REASONS else ("completed" if status == "accepted" else "rejected")
        return Acknowledgement(packet.event_id, packet.endpoint_id, self.gateway_id, status, action, reason, self.policy_version, utc_now(), terminal)

    def _reject(self, packet: ECGPacket, reason: str) -> Acknowledgement:
        ack = self._ack(packet, "rejected", "reject", reason)
        self.store.record(packet.event_id, packet.endpoint_id, utc_now(), packet.to_dict(), "rejected", ack.to_dict())
        return ack

    def accept(self, payload: dict, event_factory) -> Acknowledgement:
        try:
            packet = ECGPacket.from_dict(payload)
        except (TypeError, ValueError) as error:
            raw = payload if isinstance(payload, dict) else {}
            identifier = str(raw.get("event_id") or f"invalid-{uuid4()}")
            endpoint = str(raw.get("endpoint_id") or "unknown-endpoint")
            reason = str(error)
            ack = Acknowledgement(identifier, endpoint, self.gateway_id, "rejected", "reject", reason, self.policy_version, utc_now(), "rejected")
            # Persist malformed events as first-class rejected attempts so the
            # Gate V audit requirement covers schema failures as well.
            self.store.record(identifier, endpoint, utc_now(), raw, "rejected", ack.to_dict())
            return ack
        existing = self.store.existing_response(packet.event_id)
        if existing is not None and existing.get("reason") not in self.RETRYABLE_REASONS:
            return Acknowledgement(**existing)
        if packet.gateway_id != self.gateway_id:
            return self._reject(packet, "gateway_id_mismatch")
        if packet.model_sha256 != self.model_sha256:
            return self._reject(packet, "model_hash_mismatch")
        if packet.policy_version != self.policy_version:
            return self._reject(packet, "policy_version_mismatch")
        if packet.contract_version != self.contract_version:
            return self._reject(packet, "contract_version_mismatch")
        try:
            timestamp = datetime.fromisoformat(packet.recorded_at.replace("Z", "+00:00")).astimezone(timezone.utc)
            if (datetime.now(timezone.utc) - timestamp).total_seconds() > self.stale_after_seconds:
                return self._reject(packet, "stale_event")
        except ValueError:
            return self._reject(packet, "malformed_schema: recorded_at")
        expected = self.next_sequence.get(packet.endpoint_id, 0)
        if packet.sample_sequence != expected:
            return self._reject(packet, "duplicate_sequence" if packet.sample_sequence < expected else "sequence_gap")
        try:
            event = event_factory(packet)
        except ValueError as error:
            return self._reject(packet, str(error))
        action = self.policy.decide(event)
        ack = self._ack(packet, "accepted", action.requested_action, action.reason)
        self.store.record(packet.event_id, packet.endpoint_id, utc_now(), {"packet": packet.to_dict(), "event": event.to_dict(), "action": action.to_dict()}, "accepted", ack.to_dict())
        self.next_sequence[packet.endpoint_id] = packet.sample_sequence + len(packet.samples)
        return ack

class LocalGatewayRuntime:
    """Bind ingestion, causal processing, frozen inference, policy, and ACKs."""

    def __init__(self, ingest: GatewayIngest, signal_processor, inference, transport) -> None:
        self.ingest = ingest
        self.signal_processor = signal_processor
        self.inference = inference
        self.transport = transport
        self.metrics: list[dict[str, float | str]] = []

    def bind_endpoint(self, endpoint_id: str) -> None:
        self.transport.subscribe(f"ecg/{endpoint_id}/samples", self.handle_packet)

    def handle_packet(self, payload: dict) -> None:
        import time

        started = time.perf_counter_ns()
        components: dict[str, float] = {}
        def event_factory(packet: ECGPacket):
            signal_started = time.perf_counter_ns()
            window, rr, quality = self.signal_processor.process(packet)
            components["signal_processing_ms"] = (time.perf_counter_ns() - signal_started) / 1e6
            probability, metadata = self.inference.infer(window, rr, quality)
            components["neural_inference_ms"] = float(metadata["inference_latency_ms"])
            from .contracts import GatewayEvent
            return GatewayEvent(
                packet.event_id, packet.endpoint_id, packet.gateway_id, packet.sample_sequence,
                packet.recorded_at, packet.lead_profile, packet.native_sample_rate_hz,
                packet.transport_profile, metadata["model_sha256"], packet.policy_version,
                quality, probability, metadata["decision_threshold"],
            )

        ack = self.ingest.accept(payload, event_factory)
        decision_finished = time.perf_counter_ns()
        topic = f"ecg/{ack.endpoint_id}/ack"
        self.ingest.store.queue_ack(ack.event_id, topic, ack.to_dict())
        ack_started = time.perf_counter_ns()
        try:
            self.transport.publish(topic, ack.to_dict())
            self.ingest.store.mark_delivered(ack.event_id)
        except Exception:
            pass
        finished = time.perf_counter_ns()
        known = components.get("signal_processing_ms", 0.0) + components.get("neural_inference_ms", 0.0)
        packetized_at = payload.get("packetized_at_monotonic_ns") if isinstance(payload, dict) else None
        self.metrics.append({
            "event_id": ack.event_id,
            "ack_status": ack.ack_status,
            "signal_processing_ms": components.get("signal_processing_ms", 0.0),
            "neural_inference_ms": components.get("neural_inference_ms", 0.0),
            "policy_audit_ms": max(0.0, (decision_finished - started) / 1e6 - known),
            "acknowledgement_ms": (finished - ack_started) / 1e6,
            "gateway_decision_ms": (decision_finished - started) / 1e6,
            "gateway_total_ms": (finished - started) / 1e6,
            "endpoint_to_gateway_ms": max(0.0, (started - packetized_at) / 1e6) if isinstance(packetized_at, int) else 0.0,
        })
