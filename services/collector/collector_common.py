"""Shared collector utilities."""

import json
from pathlib import Path

try:
    from kafka import KafkaProducer
except ImportError:  # pragma: no cover
    KafkaProducer = None


def append_local(event: dict, output_path: str = "data/raw_events.jsonl"):
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


class EventPublisher:
    def __init__(
        self,
        bootstrap: str,
        topic: str,
        fallback_path: str = "data/raw_events.jsonl",
    ):
        self.bootstrap = bootstrap
        self.topic = topic
        self.fallback_path = fallback_path
        self.producer = None

        try:
            if KafkaProducer is None:
                raise RuntimeError("kafka-python is not installed")
            self.producer = KafkaProducer(
                bootstrap_servers=bootstrap,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
            print(f"[collector] connected kafka={bootstrap}, topic={topic}")
        except Exception as exc:
            print(f"[collector] kafka unavailable, fallback local file. reason={exc}")

    def publish(self, event: dict):
        if self.producer is not None:
            try:
                self.producer.send(self.topic, event)
                return
            except Exception as exc:
                print(f"[collector] send failed, write local. reason={exc}")
        append_local(event, self.fallback_path)

    def publish_many(self, events: list[dict]) -> int:
        for event in events:
            self.publish(event)
        return len(events)

    def close(self):
        if self.producer is not None:
            try:
                self.producer.flush(timeout=5)
                self.producer.close()
            except Exception:
                pass
