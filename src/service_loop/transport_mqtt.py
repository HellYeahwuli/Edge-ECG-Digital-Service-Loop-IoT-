"""Local MQTT v5 adapter and deterministic in-process test transport."""

from __future__ import annotations

import json
import threading
from collections import defaultdict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor


class InMemoryTransport:
    """Synchronous local test transport; not evidence of MQTT performance."""

    profile = "simulated_in_memory_transport"

    def __init__(self) -> None:
        self._subscriptions: dict[str, list[Callable[[dict], None]]] = defaultdict(list)

    def subscribe(self, topic: str, callback: Callable[[dict], None]) -> None:
        self._subscriptions[topic].append(callback)

    def publish(self, topic: str, payload: dict) -> None:
        for callback in tuple(self._subscriptions.get(topic, ())):
            callback(payload)


class LocalMqttV5Transport:
    """MQTT v5 QoS 1 adapter; the broker must be local and user-provided."""

    profile = "local_mqtt_v5_qos1"

    def __init__(self, host: str = "127.0.0.1", port: int = 1883) -> None:
        try:
            import paho.mqtt.client as mqtt
        except ImportError as error:
            raise RuntimeError("paho-mqtt is required for local MQTT 8A execution") from error
        self._callbacks: dict[str, list[Callable[[dict], None]]] = defaultdict(list)
        self._subscription_events: dict[int, threading.Event] = {}
        self._completed_subscriptions: set[int] = set()
        self._connected = threading.Event()
        self._connection_error: str | None = None
        self._callback_errors: list[str] = []
        self._closing = False
        # Keep application callbacks off Paho's network-loop thread.  Gateway
        # callbacks publish QoS 1 ACKs and may wait for PUBACK; doing that on
        # the network-loop thread would deadlock the broker handshake.
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ecg-mqtt-callback")
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.on_subscribe = self._on_subscribe
        self._client.connect(host, port, keepalive=30)
        self._client.loop_start()
        if not self._connected.wait(5.0):
            self.close()
            detail = self._connection_error or "timeout"
            raise RuntimeError(f"local MQTT broker connection failed: {detail}")

    def _on_connect(self, _client, _userdata, _flags, reason_code, _properties=None) -> None:
        value = getattr(reason_code, "value", reason_code)
        if value == 0:
            self._connected.set()
        else:
            self._connection_error = f"reason_code={reason_code}"

    def _on_disconnect(self, _client, _userdata, _disconnect_flags, reason_code, _properties=None) -> None:
        value = getattr(reason_code, "value", reason_code)
        if value != 0:
            self._connection_error = f"reason_code={reason_code}"

    @property
    def callback_errors(self) -> list[str]:
        return list(self._callback_errors)

    def _on_message(self, _client, _userdata, message) -> None:
        if self._closing:
            return
        payload = json.loads(message.payload.decode("utf-8"))
        for callback in tuple(self._callbacks.get(message.topic, ())):
            self._executor.submit(self._dispatch, callback, payload)

    def _dispatch(self, callback: Callable[[dict], None], payload: dict) -> None:
        try:
            callback(payload)
        except Exception as error:
            self._callback_errors.append(f"{type(error).__name__}: {error}")

    def _on_subscribe(self, _client, _userdata, mid, _reason_code_list, _properties=None) -> None:
        event = self._subscription_events.get(mid)
        if event:
            event.set()
        else:
            self._completed_subscriptions.add(mid)

    def subscribe(self, topic: str, callback: Callable[[dict], None]) -> None:
        self._callbacks[topic].append(callback)
        result, mid = self._client.subscribe(topic, qos=1)
        if result != 0:
            raise RuntimeError(f"MQTT subscribe failed: rc={result}")
        event = threading.Event()
        self._subscription_events[mid] = event
        if mid in self._completed_subscriptions:
            self._completed_subscriptions.remove(mid)
            event.set()
        if not event.wait(2.0):
            self._subscription_events.pop(mid, None)
            raise RuntimeError(f"MQTT subscribe acknowledgement timed out: {topic}")
        self._subscription_events.pop(mid, None)

    def publish(self, topic: str, payload: dict) -> None:
        result = self._client.publish(topic, json.dumps(payload, separators=(",", ":")), qos=1)
        result.wait_for_publish(timeout=5.0)
        if result.rc != 0 or not result.is_published():
            raise RuntimeError(f"MQTT publish failed: rc={result.rc}")

    def close(self) -> None:
        self._closing = True
        self._executor.shutdown(wait=True)
        self._client.loop_stop()
        self._client.disconnect()
