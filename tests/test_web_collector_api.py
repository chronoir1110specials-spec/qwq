import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "apps" / "backend"))

from app import create_app  # noqa: E402
import app.routes as routes  # noqa: E402


class FakeBridge:
    def __init__(self):
        self.started = None
        self.stopped = False

    def snapshot(self, limit_events=20, limit_logs=30):
        return {
            "runtime": {
                "available": True,
                "source_dir": "D:/fake/Tiktok-live",
                "missing_dependencies": [],
                "missing_files": [],
            },
            "collector": {
                "running": bool(self.started and not self.stopped),
                "thread_alive": bool(self.started and not self.stopped),
                "live_id": self.started["live_id"] if self.started else "live_001",
                "web_rid": self.started["web_rid"] if self.started else "123456",
                "room_id": "99887766",
                "anchor_id": self.started["anchor_id"] if self.started else "",
                "status_text": "正在直播",
                "anchor_nickname": "测试主播",
                "anchor_user_id": "anchor_001",
                "last_error": "",
                "last_log_at": "2026-03-20T00:00:00+00:00",
                "last_event_at": "2026-03-20T00:00:00+00:00",
                "total_events": 3,
                "current_online_users": 2333,
                "total_viewers": 4567,
                "event_counts": {"comment": 1, "like": 2},
            },
            "recent_events": [
                {
                    "event_time": "2026-03-20T00:00:00+00:00",
                    "event_type": "comment",
                    "user_id": "u001",
                    "user_name": "Alice",
                    "comment": "hello",
                    "online_users": 2333,
                }
            ][:limit_events],
            "recent_logs": [
                {"ts": "2026-03-20T00:00:00+00:00", "type": "WEBSOCKET", "message": "connected"}
            ][-limit_logs:],
            "audience": [
                {"rank": 1, "user_id": "u001", "nickname": "Alice", "display_id": "alice001"}
            ],
        }

    def inspect_room(self, live_id, web_rid):
        return {
            "ok": True,
            "live_id": live_id,
            "web_rid": web_rid,
            "room_id": "99887766",
            "room_status": 0,
            "status_text": "正在直播",
            "anchor_nickname": "测试主播",
            "anchor_user_id": "anchor_001",
        }

    def inspect_audience(self, live_id, web_rid, anchor_id):
        return [
            {"rank": 1, "user_id": "u001", "nickname": f"{live_id}-{web_rid}-{anchor_id}", "display_id": "id001"}
        ]

    def start(self, live_id, web_rid, anchor_id=""):
        self.started = {"live_id": live_id, "web_rid": web_rid, "anchor_id": anchor_id}
        self.stopped = False
        return {"ok": True, "snapshot": self.snapshot()}

    def stop(self):
        self.stopped = True
        return {"ok": True, "snapshot": self.snapshot()}

    def analytics(self, live_id, max_points=30):
        if live_id != "live_001":
            return None
        return {
            "mode": "collector",
            "live_id": live_id,
            "overview": {
                "online_users": 2333,
                "likes": 88,
                "gifts": 6,
                "gift_value": 120.5,
                "comment_count": 3,
                "interaction_users": 2,
                "updated_at": "2026-03-20T00:00:00+00:00",
            },
            "trend": {
                "points": [
                    {
                        "ts": "2026-03-20T00:00:00+00:00",
                        "online_users": 2333,
                        "interaction_count": 4,
                    }
                ][:max_points]
            },
            "heatmap": {"items": [{"minute_slot": "08:00", "interaction_count": 4}]},
            "funnel": {
                "stages": [
                    {"name": "当前触达", "value": 2333},
                    {"name": "互动用户", "value": 2},
                    {"name": "评论用户", "value": 1},
                    {"name": "送礼用户", "value": 1},
                ]
            },
            "sentiment": {"summary": {"positive": 1, "neutral": 1, "negative": 1}, "comment_count": 3},
            "top_users": {"users": [{"user_id": "Alice", "comments": 1, "likes": 2, "gifts": 1, "score": 12}]},
            "insights": {"items": ["test insight"]},
            "meta": {"room_id": "99887766", "anchor_nickname": "主播A"},
        }


def build_client(monkeypatch):
    fake = FakeBridge()
    monkeypatch.setattr(routes, "get_web_collector_bridge", lambda: fake)
    app = create_app()
    return app.test_client(), fake


def test_web_collector_snapshot(monkeypatch):
    client, _fake = build_client(monkeypatch)

    resp = client.get("/api/collector/web/snapshot?limit_events=5&limit_logs=5")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["runtime"]["available"] is True
    assert data["collector"]["room_id"] == "99887766"
    assert data["recent_events"][0]["event_type"] == "comment"


def test_web_collector_start(monkeypatch):
    client, fake = build_client(monkeypatch)

    resp = client.post(
        "/api/collector/web/start",
        json={"live_id": "live_002", "web_rid": "261378947940", "anchor_id": "138960285477659"},
    )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert fake.started == {
        "live_id": "live_002",
        "web_rid": "261378947940",
        "anchor_id": "138960285477659",
    }


def test_web_collector_audience(monkeypatch):
    client, _fake = build_client(monkeypatch)

    resp = client.get(
        "/api/collector/web/audience?live_id=live_003&web_rid=abc123&anchor_id=anchor007"
    )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert data["items"][0]["nickname"] == "live_003-abc123-anchor007"


def test_web_collector_analytics(monkeypatch):
    client, _fake = build_client(monkeypatch)

    resp = client.get("/api/collector/web/analytics/live_001?limit=12")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["mode"] == "collector"
    assert data["overview"]["online_users"] == 2333
    assert data["funnel"]["stages"][0]["name"] == "当前触达"
