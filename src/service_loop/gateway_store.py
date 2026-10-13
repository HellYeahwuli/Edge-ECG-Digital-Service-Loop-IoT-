"""SQLite WAL audit store with event idempotency and recoverable outbox state."""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path


class GatewayStore:
    def __init__(self, path: Path) -> None:
        self._lock = threading.RLock()
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA busy_timeout=5000")
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                endpoint_id TEXT NOT NULL,
                received_at TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                status TEXT NOT NULL,
                response_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS event_attempts (
                attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL,
                endpoint_id TEXT NOT NULL,
                received_at TEXT NOT NULL,
                status TEXT NOT NULL,
                reason TEXT NOT NULL,
                response_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS outbox (
                event_id TEXT PRIMARY KEY,
                topic TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                next_retry_at TEXT,
                terminal_status TEXT NOT NULL DEFAULT 'pending'
            );
        """)
        self.connection.commit()

    def existing_response(self, event_id: str) -> dict | None:
        with self._lock:
            row = self.connection.execute("SELECT response_json FROM events WHERE event_id = ?", (event_id,)).fetchone()
        return json.loads(row["response_json"]) if row else None

    def record(self, event_id: str, endpoint_id: str, received_at: str, payload: dict, status: str, response: dict) -> None:
        reason = str(response.get("reason", ""))
        with self._lock:
            self.connection.execute(
                "INSERT OR REPLACE INTO events(event_id, endpoint_id, received_at, payload_json, status, response_json) VALUES (?, ?, ?, ?, ?, ?)",
                (event_id, endpoint_id, received_at, json.dumps(payload), status, json.dumps(response)),
            )
            self.connection.execute(
                "INSERT INTO event_attempts(event_id, endpoint_id, received_at, status, reason, response_json) VALUES (?, ?, ?, ?, ?, ?)",
                (event_id, endpoint_id, received_at, status, reason, json.dumps(response)),
            )
            self.connection.commit()

    def queue_ack(self, event_id: str, topic: str, payload: dict) -> None:
        with self._lock:
            self.connection.execute(
                "INSERT OR REPLACE INTO outbox(event_id, topic, payload_json, attempts, terminal_status) VALUES (?, ?, ?, 0, 'pending')",
                (event_id, topic, json.dumps(payload)),
            )
            self.connection.commit()

    def pending_outbox(self) -> list[sqlite3.Row]:
        with self._lock:
            return list(self.connection.execute("SELECT * FROM outbox WHERE terminal_status = 'pending' ORDER BY rowid"))

    def mark_delivered(self, event_id: str) -> None:
        with self._lock:
            self.connection.execute("UPDATE outbox SET terminal_status = 'delivered' WHERE event_id = ?", (event_id,))
            self.connection.commit()

    def mark_attempt(self, event_id: str, terminal_status: str) -> None:
        with self._lock:
            self.connection.execute("UPDATE outbox SET attempts = attempts + 1, terminal_status = ? WHERE event_id = ?", (terminal_status, event_id))
            self.connection.commit()

    def close(self) -> None:
        with self._lock:
            self.connection.close()

    def audit_count(self) -> int:
        with self._lock:
            return int(self.connection.execute("SELECT COUNT(*) FROM events").fetchone()[0])

    def attempt_count(self) -> int:
        with self._lock:
            return int(self.connection.execute("SELECT COUNT(*) FROM event_attempts").fetchone()[0])

    def accepted_count(self) -> int:
        with self._lock:
            return int(self.connection.execute("SELECT COUNT(*) FROM events WHERE status = 'accepted'").fetchone()[0])

    def rejected_count(self) -> int:
        with self._lock:
            return int(self.connection.execute("SELECT COUNT(*) FROM events WHERE status = 'rejected'").fetchone()[0])

    def accepted_audit_completeness(self) -> dict[str, float | int]:
        """Check the Gate V provenance fields on the latest accepted event state."""
        required_packet = ("event_id", "endpoint_id", "gateway_id", "sample_sequence", "recorded_at", "lead_profile", "native_sample_rate_hz", "transport_profile", "model_sha256", "policy_version", "contract_version")
        required_event = ("event_id", "endpoint_id", "gateway_id", "signal_quality", "pvc_probability", "decision_threshold", "r_peak_source", "contract_version")
        required_action = ("event_id", "endpoint_id", "gateway_id", "policy_version", "requested_action", "status", "reason", "created_at", "contract_version")
        with self._lock:
            rows = self.connection.execute("SELECT event_id, payload_json, response_json FROM events WHERE status = 'accepted'").fetchall()
            complete = 0
            for row in rows:
                payload = json.loads(row["payload_json"])
                ack = json.loads(row["response_json"])
                packet, event, action = payload.get("packet", {}), payload.get("event", {}), payload.get("action", {})
                outbox = self.connection.execute("SELECT terminal_status FROM outbox WHERE event_id = ?", (row["event_id"],)).fetchone()
                fields_ok = all(packet.get(name) not in (None, "") for name in required_packet)
                fields_ok = fields_ok and all(event.get(name) not in (None, "") for name in required_event)
                fields_ok = fields_ok and all(action.get(name) not in (None, "") for name in required_action)
                fields_ok = fields_ok and all(ack.get(name) not in (None, "") for name in ("event_id", "endpoint_id", "gateway_id", "ack_status", "requested_action", "reason", "policy_version", "acknowledged_at", "terminal_status", "contract_version"))
                fields_ok = fields_ok and outbox is not None and outbox["terminal_status"] not in (None, "")
                complete += int(fields_ok)
        total = len(rows)
        return {"accepted_events": total, "complete_events": complete, "completeness": (complete / total if total else 1.0)}

    def rejected_reason_completeness(self) -> dict[str, float | int]:
        with self._lock:
            rows = self.connection.execute("SELECT COUNT(*) AS total, SUM(CASE WHEN reason <> '' THEN 1 ELSE 0 END) AS with_reason FROM event_attempts WHERE status = 'rejected'").fetchone()
        total = int(rows["total"] or 0)
        with_reason = int(rows["with_reason"] or 0)
        return {"rejected_attempts": total, "with_reason": with_reason, "completeness": (with_reason / total if total else 1.0)}

    def latest_events(self) -> list[dict]:
        with self._lock:
            rows = self.connection.execute("SELECT * FROM events ORDER BY rowid").fetchall()
        return [dict(row) for row in rows]

    def next_sequence_map(self) -> dict[str, int]:
        """Recover endpoint sequence state from accepted WAL-backed events."""
        with self._lock:
            rows = self.connection.execute("SELECT endpoint_id, payload_json FROM events WHERE status = 'accepted' ORDER BY rowid").fetchall()
        result: dict[str, int] = {}
        for row in rows:
            payload = json.loads(row["payload_json"])
            packet = payload.get("packet", {})
            sequence = packet.get("sample_sequence")
            samples = packet.get("samples")
            if isinstance(sequence, int) and isinstance(samples, list):
                result[row["endpoint_id"]] = max(result.get(row["endpoint_id"], 0), sequence + len(samples))
        return result
