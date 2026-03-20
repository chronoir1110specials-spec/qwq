"""Simulated event source used for local demos."""

import random
import time
from datetime import datetime, timezone

from collector_common import EventPublisher


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
    "Nice host",
    "Looks good",
    "Price looks high",
    "How long is shipping",
    "Support the streamer",
    "Adding to cart first",
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


def build_rng(live_id: str, seed: int | None) -> random.Random:
    live_bias = sum(ord(ch) for ch in live_id)
    if seed is None:
        return random.Random(time.time_ns() + live_bias)
    return random.Random(seed + live_bias)


def run_simulated(
    publisher: EventPublisher,
    live_id: str,
    interval: float,
    seed: int | None,
):
    rng = build_rng(live_id, seed)
    while True:
        event = generate_event(live_id, rng)
        publisher.publish(event)
        print(f"[collector] simulated {event['event_type']} user={event['user_id']}")
        time.sleep(interval)
