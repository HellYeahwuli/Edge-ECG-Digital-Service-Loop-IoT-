from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path

from service_loop.contracts import GatewayEvent
from service_loop.endpoint_replay import ReplayEndpoint
from service_loop.gateway_ingest import GatewayIngest
from service_loop.gateway_policy import PolicyV1
from service_loop.gateway_store import GatewayStore


class ServiceLoopContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.store = GatewayStore(Path(self.directory.name) / "gateway.sqlite")
        self.policy = PolicyV1()
        self.model_hash = "test-model-hash"
        self.ingest = GatewayIngest("gateway-test", self.model_hash, self.policy.version, self.store, self.policy)
        self.endpoint = ReplayEndpoint("endpoint-test", "gateway-test", "two_channel", 360, self.model_hash, self.policy.version)

    def tearDown(self) -> None:
        self.store.close()
        self.directory.cleanup()

    def event_factory(self, packet):
        return GatewayEvent(
            packet.event_id, packet.endpoint_id, packet.gateway_id, packet.sample_sequence,
            packet.recorded_at, packet.lead_profile, packet.native_sample_rate_hz,
            packet.transport_profile, packet.model_sha256, packet.policy_version,
            0.95, 0.95, 0.80,
        )

    def test_duplicate_event_is_idempotent(self) -> None:
        packet = self.endpoint.packet([[0.0, 0.0]] * 300, event_id="same-event")
        first = self.ingest.accept(packet.to_dict(), self.event_factory)
        second = self.ingest.accept(packet.to_dict(), self.event_factory)
        self.assertEqual(first, second)
        self.assertEqual(self.store.audit_count(), 1)

    def test_sequence_gap_is_rejected(self) -> None:
        first = self.endpoint.packet([[0.0, 0.0]] * 300)
        self.assertEqual(self.ingest.accept(first.to_dict(), self.event_factory).ack_status, "accepted")
        gap = self.endpoint.packet([[0.0, 0.0]] * 300)
        payload = gap.to_dict()
        payload["sample_sequence"] += 1
        self.assertEqual(self.ingest.accept(payload, self.event_factory).reason, "sequence_gap")

    def test_first_observed_packet_must_start_at_zero(self) -> None:
        packet = self.endpoint.packet([[0.0, 0.0]] * 300)
        payload = packet.to_dict()
        payload["sample_sequence"] = 300
        self.assertEqual(self.ingest.accept(payload, self.event_factory).reason, "sequence_gap")

    def test_sequence_gap_can_be_retried_after_missing_packet(self) -> None:
        first = self.endpoint.packet([[0.0, 0.0]] * 300, event_id="ordered-0")
        missing = self.endpoint.packet([[0.0, 0.0]] * 300, event_id="ordered-1")
        out_of_order = self.endpoint.packet([[0.0, 0.0]] * 300, event_id="ordered-2")
        self.assertEqual(self.ingest.accept(first.to_dict(), self.event_factory).ack_status, "accepted")
        self.assertEqual(self.ingest.accept(out_of_order.to_dict(), self.event_factory).reason, "sequence_gap")
        self.assertEqual(self.ingest.accept(missing.to_dict(), self.event_factory).ack_status, "accepted")
        self.assertEqual(self.ingest.accept(out_of_order.to_dict(), self.event_factory).ack_status, "accepted")
        self.assertEqual(self.store.accepted_count(), 3)

    def test_malformed_event_is_persisted_with_reason(self) -> None:
        ack = self.ingest.accept({"event_id": "malformed", "endpoint_id": self.endpoint.endpoint_id}, self.event_factory)
        self.assertEqual(ack.ack_status, "rejected")
        self.assertEqual(self.store.rejected_reason_completeness()["completeness"], 1.0)

    def test_model_hash_mismatch_is_rejected(self) -> None:
        packet = self.endpoint.packet([[0.0, 0.0]] * 300)
        payload = packet.to_dict()
        payload["model_sha256"] = "incorrect"
        self.assertEqual(self.ingest.accept(payload, self.event_factory).reason, "model_hash_mismatch")

    def test_contract_version_mismatch_is_rejected_and_audited(self) -> None:
        packet = self.endpoint.packet([[0.0, 0.0]] * 300)
        payload = packet.to_dict()
        payload["contract_version"] = "unsupported-contract"
        ack = self.ingest.accept(payload, self.event_factory)
        self.assertEqual(ack.reason, "contract_version_mismatch")
        self.assertEqual(self.store.rejected_reason_completeness()["completeness"], 1.0)

    def test_third_risk_event_requests_review(self) -> None:
        actions = []
        for index in range(3):
            packet = self.endpoint.packet([[0.0, 0.0]] * 300, event_id=f"risk-{index}")
            actions.append(self.ingest.accept(packet.to_dict(), self.event_factory).requested_action)
        self.assertEqual(actions, ["buffer_segment", "buffer_segment", "request_review"])

    def test_gateway_store_accepts_callback_thread(self) -> None:
        packet = self.endpoint.packet([[0.0, 0.0]] * 300, event_id="threaded-event")
        acknowledgements = []
        thread = threading.Thread(target=lambda: acknowledgements.append(self.ingest.accept(packet.to_dict(), self.event_factory)))
        thread.start()
        thread.join(timeout=2.0)
        self.assertFalse(thread.is_alive())
        self.assertEqual(acknowledgements[0].ack_status, "accepted")


if __name__ == "__main__":
    unittest.main()
