import json
import os
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone

try:
    from kafka import KafkaConsumer
except ImportError:  # pragma: no cover
    KafkaConsumer = None


def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


class RealtimeMetricsStore:
    def __init__(self):
        self.bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.topic = os.getenv("KAFKA_METRICS_TOPIC", "live_metrics")
        self.max_points = _to_int(os.getenv("REALTIME_MAX_POINTS", "500"), 500)

        self._buffers = defaultdict(lambda: deque(maxlen=self.max_points))
        self._lock = threading.Lock()
        self._thread = None
        self._stop_event = threading.Event()
        self._status = {
            "running": False,
            "last_error": "",
            "last_message_at": "",
            "topic": self.topic,
            "bootstrap": self.bootstrap,
        }

    def ensure_started(self):
        if self._thread and self._thread.is_alive():
            return
        if KafkaConsumer is None:
            self._status["last_error"] = "kafka-python is not installed."
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._consume_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    def _consume_loop(self):
        while not self._stop_event.is_set():
            consumer = None
            try:
                consumer = KafkaConsumer(
                    self.topic,
                    bootstrap_servers=self.bootstrap,
                    auto_offset_reset="latest",
                    enable_auto_commit=True,
                    value_deserializer=lambda b: json.loads(b.decode("utf-8")),
                    consumer_timeout_ms=1000,
                )
                self._status["running"] = True
                self._status["last_error"] = ""

                while not self._stop_event.is_set():
                    polled = consumer.poll(timeout_ms=1000, max_records=500)
                    for records in polled.values():
                        for record in records:
                            self._on_record(record.value)
            except Exception as exc:  # pragma: no cover
                self._status["running"] = False
                self._status["last_error"] = str(exc)
                time.sleep(2)
            finally:
                if consumer is not None:
                    try:
                        consumer.close()
                    except Exception:
                        pass

    def _on_record(self, raw: dict):
        live_id = str(raw.get("live_id", "")).strip()
        if not live_id:
            return

        point = {
            "window_start": str(raw.get("window_start", "")),
            "window_end": str(raw.get("window_end", "")),
            "live_id": live_id,
            "avg_online_users": round(_to_float(raw.get("avg_online_users")), 2),
            "like_events": _to_int(raw.get("like_events")),
            "gift_events": _to_int(raw.get("gift_events")),
            "gift_value_sum": round(_to_float(raw.get("gift_value_sum")), 2),
            "interaction_events": _to_int(raw.get("interaction_events")),
        }

        with self._lock:
            self._buffers[live_id].append(point)
            self._status["last_message_at"] = datetime.now(timezone.utc).isoformat()

    def get_snapshot(self, live_id: str, limit: int = 60):
        with self._lock:
            points = list(self._buffers.get(live_id, deque()))[-limit:]
            status = dict(self._status)
        latest = points[-1] if points else None
        return {
            "live_id": live_id,
            "latest": latest,
            "points": points,
            "status": status,
        }


_REALTIME_STORE = RealtimeMetricsStore()


def get_realtime_store() -> RealtimeMetricsStore:
    return _REALTIME_STORE
