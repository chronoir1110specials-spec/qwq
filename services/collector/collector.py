import argparse
import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path

from kafka import KafkaProducer


EVENT_TYPES = [
    "enter",
    "leave",
    "like",
    "gift",
    "comment",
    "product_click",
    "purchase",
]

COMMENTS = [
    "主播讲得好",
    "这款不错",
    "价格有点高",
    "发货快吗",
    "支持一下",
    "先加购",
]


def generate_event(live_id: str, rng: random.Random) -> dict:
    event_type = rng.choice(EVENT_TYPES)
    return {
        "event_time": datetime.now(timezone.utc).isoformat(),
        "live_id": live_id,
        "user_id": f"u{rng.randint(1, 5000):04d}",
        "event_type": event_type,
        "online_users": rng.randint(3000, 15000),
        "like_count": rng.randint(0, 10),
        "gift_value": round(rng.uniform(0, 120), 2) if event_type == "gift" else 0.0,
        "product_id": f"p{rng.randint(1000, 1020)}" if event_type in ("product_click", "purchase") else "",
        "product_action": event_type if event_type in ("product_click", "purchase") else "",
        "comment": rng.choice(COMMENTS) if event_type == "comment" else "",
    }


def append_local(event: dict):
    output = Path("data/raw_events.jsonl")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def _build_rng(live_id: str, seed: int | None) -> random.Random:
    live_bias = sum(ord(ch) for ch in live_id)
    if seed is None:
        return random.Random(time.time_ns() + live_bias)
    return random.Random(seed + live_bias)


def run(bootstrap: str, topic: str, live_id: str, interval: float, seed: int | None):
    rng = _build_rng(live_id, seed)
    producer = None
    try:
        producer = KafkaProducer(
            bootstrap_servers=bootstrap,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        print(f"[collector] connected kafka={bootstrap}, topic={topic}")
    except Exception as exc:
        print(f"[collector] kafka unavailable, fallback local file. reason={exc}")

    while True:
        event = generate_event(live_id, rng)
        if producer is not None:
            try:
                producer.send(topic, event)
            except Exception as exc:
                print(f"[collector] send failed, write local. reason={exc}")
                append_local(event)
        else:
            append_local(event)
        print(f"[collector] {event['event_type']} user={event['user_id']}")
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="Douyin live event collector (MVP)")
    parser.add_argument("--bootstrap", default="localhost:9092")
    parser.add_argument("--topic", default="live_events")
    parser.add_argument("--live-id", default="live_001")
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()
    run(args.bootstrap, args.topic, args.live_id, args.interval, args.seed)


if __name__ == "__main__":
    main()
