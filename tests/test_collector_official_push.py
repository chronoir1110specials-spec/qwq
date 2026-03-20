import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "services" / "collector"))

from collector_official_push import (  # noqa: E402
    LiveRoomBinding,
    OfficialPayloadAdapter,
    OfficialPushSettings,
)


def build_settings() -> OfficialPushSettings:
    return OfficialPushSettings(
        bind_host="0.0.0.0",
        bind_port=9100,
        webhook_path="/webhook/douyin/live",
        verification_token="",
        bindings=[
            LiveRoomBinding(
                live_id="live_001",
                room_id="544590831076",
                anchor_id="138960285477659",
            )
        ],
    )


def test_normalize_comment_payload_by_room_id():
    adapter = OfficialPayloadAdapter(build_settings())
    payload = {
        "event_type": "comment",
        "room_id": "544590831076",
        "user": {"id": "u1234"},
        "content": "hello world",
        "online_users": 3210,
    }

    events = adapter.normalize(payload)

    assert len(events) == 1
    assert events[0]["live_id"] == "live_001"
    assert events[0]["event_type"] == "comment"
    assert events[0]["user_id"] == "u1234"
    assert events[0]["comment"] == "hello world"
    assert events[0]["online_users"] == 3210


def test_normalize_wrapped_gift_payload():
    adapter = OfficialPayloadAdapter(build_settings())
    payload = {
        "data": {
            "events": [
                {
                    "type": "gift",
                    "room_id": "544590831076",
                    "from_user_id": "u5678",
                    "gift_value": 88.6,
                }
            ]
        }
    }

    events = adapter.normalize(payload)

    assert len(events) == 1
    assert events[0]["live_id"] == "live_001"
    assert events[0]["event_type"] == "gift"
    assert events[0]["user_id"] == "u5678"
    assert events[0]["gift_value"] == 88.6
