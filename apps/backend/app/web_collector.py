from __future__ import annotations

import os
import sys
import threading
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[3]
COLLECTOR_DIR = ROOT_DIR / "services" / "collector"
if str(COLLECTOR_DIR) not in sys.path:
    sys.path.insert(0, str(COLLECTOR_DIR))

from collector_common import EventPublisher  # noqa: E402
from collector_web_live import (  # noqa: E402
    DouyinWebLiveCollector,
    get_web_live_runtime,
    inspect_web_live_audience,
    inspect_web_live_room,
)
from .sentiment import analyze_text


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_event_time(value) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _bucket_dt(dt: datetime, bucket_seconds: int = 30) -> datetime:
    normalized = dt.astimezone(timezone.utc)
    second = (normalized.second // bucket_seconds) * bucket_seconds
    return normalized.replace(second=second, microsecond=0)


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _gift_units(event: dict) -> int:
    return max(1, _safe_int(event.get("gift_count"), 0))


_EVENT_TYPE_LABELS = {
    "comment": "评论",
    "emoji": "表情",
    "like": "点赞",
    "gift": "礼物",
    "enter": "进房",
    "follow": "关注",
    "fansclub": "粉丝团",
    "room_stats": "房间统计",
    "room_control": "房间状态",
}


class WebCollectorBridge:
    def __init__(self):
        self.bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.topic = os.getenv("KAFKA_EVENTS_TOPIC", "live_events")
        self.source_dir = os.getenv("DOUYIN_WEB_LIVE_SOURCE_DIR", "")

        self._lock = threading.Lock()
        self._collector: DouyinWebLiveCollector | None = None
        self._publisher: EventPublisher | None = None
        self._thread: threading.Thread | None = None
        self._recent_events: deque[dict] = deque(maxlen=1500)
        self._recent_logs: deque[dict] = deque(maxlen=120)
        self._audience: list[dict] = []
        self._event_counts: Counter[str] = Counter()
        self._collector_state = {
            "running": False,
            "thread_alive": False,
            "live_id": "",
            "web_rid": "",
            "room_id": "",
            "anchor_id": "",
            "status_text": "",
            "anchor_nickname": "",
            "anchor_user_id": "",
            "last_error": "",
            "last_log_at": "",
            "last_event_at": "",
            "total_events": 0,
            "current_online_users": 0,
            "total_viewers": 0,
        }

    def _runtime(self) -> dict:
        return get_web_live_runtime(self.source_dir)

    def _sync_thread_state(self) -> None:
        if self._thread is not None and not self._thread.is_alive():
            self._collector_state["thread_alive"] = False
            self._collector_state["running"] = False

    def _set_room_info(self, room_info: dict) -> None:
        self._collector_state["room_id"] = str(room_info.get("room_id", ""))
        self._collector_state["status_text"] = str(room_info.get("status_text", ""))
        self._collector_state["anchor_nickname"] = str(room_info.get("anchor_nickname", ""))
        self._collector_state["anchor_user_id"] = str(room_info.get("anchor_user_id", ""))

    def _on_log(self, log_type: str, message: str) -> None:
        entry = {"ts": _iso_now(), "type": log_type, "message": message}
        with self._lock:
            self._recent_logs.append(entry)
            self._collector_state["last_log_at"] = entry["ts"]
            if log_type == "ERROR":
                self._collector_state["last_error"] = message
            if log_type == "WEBSOCKET" and "closed" in message.lower():
                self._collector_state["running"] = False
                self._collector_state["thread_alive"] = False

    def _on_event(self, event: dict) -> None:
        with self._lock:
            self._recent_events.appendleft(event)
            self._collector_state["last_event_at"] = str(event.get("event_time", ""))
            self._collector_state["total_events"] += 1
            event_type = str(event.get("event_type", "unknown")).strip() or "unknown"
            self._event_counts[event_type] += 1
            online_users = _safe_int(event.get("online_users"), 0)
            if online_users > 0:
                self._collector_state["current_online_users"] = online_users
            total_viewers = _safe_int(event.get("total_viewers"), 0)
            if total_viewers > 0:
                self._collector_state["total_viewers"] = max(
                    self._collector_state["total_viewers"],
                    total_viewers,
                )

    def snapshot(self, limit_events: int = 20, limit_logs: int = 30) -> dict:
        limit_events = max(1, min(int(limit_events), 80))
        limit_logs = max(1, min(int(limit_logs), 120))
        with self._lock:
            self._sync_thread_state()
            collector = dict(self._collector_state)
            collector["event_counts"] = dict(self._event_counts)
            recent_events = list(self._recent_events)[:limit_events]
            recent_logs = list(self._recent_logs)[-limit_logs:]
            audience = list(self._audience)
        return {
            "runtime": self._runtime(),
            "collector": collector,
            "recent_events": recent_events,
            "recent_logs": recent_logs,
            "audience": audience,
        }

    def inspect_room(self, live_id: str, web_rid: str) -> dict:
        room_info = inspect_web_live_room(web_rid=web_rid, live_id=live_id, source_dir=self.source_dir)
        with self._lock:
            self._collector_state["live_id"] = str(live_id)
            self._collector_state["web_rid"] = str(web_rid)
            self._set_room_info(room_info)
            self._collector_state["last_error"] = ""
        self._on_log("STATUS", f"已完成直播状态探测：web_rid={web_rid} room_id={room_info.get('room_id', '-')}")
        return room_info

    def inspect_audience(self, live_id: str, web_rid: str, anchor_id: str) -> list[dict]:
        items = inspect_web_live_audience(
            web_rid=web_rid,
            anchor_id=anchor_id,
            live_id=live_id,
            source_dir=self.source_dir,
        )
        with self._lock:
            self._audience = items
            self._collector_state["anchor_id"] = str(anchor_id)
            self._collector_state["live_id"] = str(live_id)
            self._collector_state["web_rid"] = str(web_rid)
            self._collector_state["last_error"] = ""
        self._on_log("RANK", f"已获取观众榜：web_rid={web_rid} anchor_id={anchor_id} count={len(items)}")
        return items

    def _run_forever(self, collector: DouyinWebLiveCollector, publisher: EventPublisher) -> None:
        try:
            collector.start()
        except Exception as exc:
            self._on_log("ERROR", f"web live collector stopped with error: {exc}")
        finally:
            publisher.close()
            with self._lock:
                self._collector_state["running"] = False
                self._collector_state["thread_alive"] = False
                self._collector = None
                self._publisher = None
                self._thread = None

    def start(self, live_id: str, web_rid: str, anchor_id: str = "") -> dict:
        self.stop()
        runtime = self._runtime()
        if not runtime["available"]:
            detail = []
            if runtime["missing_dependencies"]:
                detail.append(f"missing dependencies: {', '.join(runtime['missing_dependencies'])}")
            if runtime["missing_files"]:
                detail.append(f"missing files: {', '.join(runtime['missing_files'])}")
            return {"ok": False, "error": "; ".join(detail) or "web live runtime unavailable", "snapshot": self.snapshot()}

        publisher = EventPublisher(self.bootstrap, self.topic)
        collector = DouyinWebLiveCollector(
            live_id=live_id,
            web_rid=web_rid,
            publisher=publisher,
            source_dir=self.source_dir,
            log_callback=self._on_log,
            event_callback=self._on_event,
        )

        with self._lock:
            self._recent_events.clear()
            self._recent_logs.clear()
            self._event_counts.clear()
            self._audience = []

        try:
            room_info = collector.get_room_status()
        except Exception as exc:
            publisher.close()
            self._on_log("ERROR", f"启动前探测失败：{exc}")
            with self._lock:
                self._collector_state["last_error"] = str(exc)
            return {"ok": False, "error": str(exc), "snapshot": self.snapshot()}

        with self._lock:
            self._collector = collector
            self._publisher = publisher
            self._collector_state.update(
                {
                    "running": True,
                    "thread_alive": True,
                    "live_id": str(live_id),
                    "web_rid": str(web_rid),
                    "anchor_id": str(anchor_id or ""),
                    "last_error": "",
                    "last_event_at": "",
                    "last_log_at": "",
                    "total_events": 0,
                    "current_online_users": 0,
                    "total_viewers": 0,
                }
            )
            self._set_room_info(room_info)

        if str(anchor_id or "").strip():
            try:
                audience = collector.get_audience_ranklist(anchor_id)
            except Exception as exc:
                self._on_log("WARN", f"failed to fetch audience ranklist: {exc}")
            else:
                with self._lock:
                    self._audience = audience

        thread = threading.Thread(target=self._run_forever, args=(collector, publisher), daemon=True)
        with self._lock:
            self._thread = thread
        thread.start()
        return {"ok": True, "snapshot": self.snapshot()}

    def stop(self) -> dict:
        with self._lock:
            collector = self._collector
            publisher = self._publisher
            thread = self._thread
            self._collector_state["running"] = False
            self._collector_state["thread_alive"] = False

        if collector is not None:
            try:
                collector.stop()
            except Exception as exc:
                self._on_log("WARN", f"failed to stop collector cleanly: {exc}")
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)
        if publisher is not None:
            publisher.close()

        with self._lock:
            self._collector = None
            self._publisher = None
            self._thread = None
        return {"ok": True, "snapshot": self.snapshot()}

    def analytics(self, live_id: str, max_points: int = 30) -> dict | None:
        max_points = max(6, min(int(max_points), 120))
        with self._lock:
            self._sync_thread_state()
            collector = dict(self._collector_state)
            if collector.get("live_id") != str(live_id):
                return None
            if not (collector.get("web_rid") or collector.get("room_id")):
                return None
            events = list(reversed(self._recent_events))
            audience = list(self._audience)
            event_counts = dict(self._event_counts)
        return self._build_analytics(
            live_id=str(live_id),
            collector=collector,
            events=events,
            audience=audience,
            event_counts=event_counts,
            max_points=max_points,
        )

    def _build_analytics(
        self,
        *,
        live_id: str,
        collector: dict,
        events: list[dict],
        audience: list[dict],
        event_counts: dict[str, int],
        max_points: int,
    ) -> dict:
        bucket_points: dict[str, dict] = {}
        minute_heatmap: defaultdict[str, int] = defaultdict(int)
        user_stats: dict[str, dict] = {}
        sentiment_counts: Counter[str] = Counter()
        sentiment_samples: list[dict] = []
        interactive_users: set[str] = set()
        comment_users: set[str] = set()
        gift_users: set[str] = set()
        like_users: set[str] = set()
        current_online = _safe_int(collector.get("current_online_users"), 0)
        total_viewers = _safe_int(collector.get("total_viewers"), 0)
        total_likes = 0
        total_gifts = 0
        total_gift_value = 0.0
        total_comments = 0
        latest_ts = ""

        for event in events:
            dt = _parse_event_time(event.get("event_time")) or _parse_event_time(collector.get("last_event_at"))
            if dt is None:
                dt = datetime.now(timezone.utc)
            latest_ts = max(latest_ts, dt.isoformat())
            minute_slot = dt.astimezone(timezone.utc).strftime("%H:%M")
            bucket = _bucket_dt(dt)
            bucket_key = bucket.isoformat()
            point = bucket_points.setdefault(
                bucket_key,
                {
                    "ts": bucket_key,
                    "online_users": 0,
                    "interaction_count": 0,
                    "like_count": 0,
                    "gift_count": 0,
                    "gift_value": 0.0,
                    "comment_count": 0,
                },
            )

            event_type = str(event.get("event_type", "unknown")).strip() or "unknown"
            user_id = str(event.get("user_id", "")).strip()
            user_name = str(event.get("user_name", "")).strip() or user_id or "-"
            online_users = _safe_int(event.get("online_users"), 0)
            if online_users > 0:
                point["online_users"] = max(point["online_users"], online_users)
                current_online = online_users
            total_viewers = max(total_viewers, _safe_int(event.get("total_viewers"), 0))

            if user_id:
                stats = user_stats.setdefault(
                    user_id,
                    {
                        "user_id": user_id,
                        "user_name": user_name,
                        "comments": 0,
                        "likes": 0,
                        "gifts": 0,
                        "gift_value": 0.0,
                        "follows": 0,
                        "enters": 0,
                    },
                )
                if not stats["user_name"] or stats["user_name"] == user_id:
                    stats["user_name"] = user_name

            interaction_delta = 0
            if event_type in {"comment", "emoji"}:
                comment_text = str(event.get("comment", "")).strip()
                total_comments += 1
                point["comment_count"] += 1
                interaction_delta = 1
                if user_id:
                    comment_users.add(user_id)
                    user_stats[user_id]["comments"] += 1
                if comment_text:
                    sentiment = analyze_text(comment_text)
                    sentiment_counts[sentiment["label"]] += 1
                    if len(sentiment_samples) < 6:
                        sentiment_samples.append(
                            {
                                "user_name": user_name,
                                "text": comment_text,
                                "label": sentiment["label"],
                            }
                        )
            elif event_type == "like":
                like_count = max(1, _safe_int(event.get("like_count"), 0))
                total_likes += like_count
                point["like_count"] += like_count
                interaction_delta = like_count
                if user_id:
                    like_users.add(user_id)
                    user_stats[user_id]["likes"] += like_count
            elif event_type == "gift":
                gift_count = _gift_units(event)
                gift_value = _safe_float(event.get("gift_value"), 0.0)
                total_gifts += gift_count
                total_gift_value += gift_value
                point["gift_count"] += gift_count
                point["gift_value"] += gift_value
                interaction_delta = gift_count
                if user_id:
                    gift_users.add(user_id)
                    user_stats[user_id]["gifts"] += gift_count
                    user_stats[user_id]["gift_value"] += gift_value
            elif event_type == "follow":
                interaction_delta = 1
                if user_id:
                    user_stats[user_id]["follows"] += 1
            elif event_type == "enter":
                interaction_delta = 1
                if user_id:
                    user_stats[user_id]["enters"] += 1

            if event_type in {"comment", "emoji", "like", "gift", "follow", "enter", "fansclub"}:
                interaction_delta = max(1, interaction_delta)
                point["interaction_count"] += interaction_delta
                minute_heatmap[minute_slot] += interaction_delta
                if user_id:
                    interactive_users.add(user_id)

        trend_points = sorted(bucket_points.values(), key=lambda item: item["ts"])[-max_points:]
        for point in trend_points:
            point["gift_value"] = round(point["gift_value"], 2)

        heatmap_items = [
            {"minute_slot": slot, "interaction_count": count}
            for slot, count in sorted(minute_heatmap.items(), key=lambda item: item[0])[-max_points:]
        ]

        touch_users = max(
            current_online,
            total_viewers,
            len(audience),
            len(interactive_users),
            len(comment_users),
            len(gift_users),
        )
        funnel_stages = [
            {"name": "当前触达", "value": touch_users},
            {"name": "互动用户", "value": len(interactive_users)},
            {"name": "评论用户", "value": len(comment_users)},
            {"name": "送礼用户", "value": len(gift_users)},
        ]

        top_users = []
        for stats in user_stats.values():
            score = (
                stats["comments"] * 4
                + stats["likes"]
                + stats["gifts"] * 6
                + stats["gift_value"] * 3
                + stats["follows"] * 4
                + stats["enters"]
            )
            top_users.append(
                {
                    "user_id": stats["user_name"] or stats["user_id"],
                    "comments": stats["comments"],
                    "likes": stats["likes"],
                    "gifts": stats["gifts"],
                    "score": round(score, 1),
                    "gift_value": round(stats["gift_value"], 2),
                }
            )
        top_users.sort(key=lambda item: (-item["score"], -item["gifts"], -item["likes"], item["user_id"]))

        total_interactions = sum(event_counts.values())
        top_event_type = max(event_counts.items(), key=lambda item: item[1])[0] if event_counts else ""
        insight_items = [
            f"当前绑定主播：{collector.get('anchor_nickname') or '未知主播'}，状态：{collector.get('status_text') or '待确认'}。",
            f"最近缓存 {len(events)} 条事件，累计 {total_interactions} 次消息，最多的是{_EVENT_TYPE_LABELS.get(top_event_type, top_event_type or '暂无')}。",
            f"点赞 {total_likes} 次，礼物 {total_gifts} 个，礼物金额 {round(total_gift_value, 2)}。",
            f"评论 {total_comments} 条，互动用户 {len(interactive_users)} 人，观众榜已抓取 {len(audience)} 人。",
        ]

        if not latest_ts:
            latest_ts = str(collector.get("last_event_at") or collector.get("last_log_at") or _iso_now())

        return {
            "mode": "collector",
            "live_id": live_id,
            "overview": {
                "online_users": current_online,
                "likes": total_likes,
                "gifts": total_gifts,
                "gift_value": round(total_gift_value, 2),
                "comment_count": total_comments,
                "interaction_users": len(interactive_users),
                "updated_at": latest_ts,
            },
            "trend": {"points": trend_points},
            "heatmap": {"items": heatmap_items},
            "funnel": {"stages": funnel_stages},
            "sentiment": {
                "summary": {
                    "positive": sentiment_counts.get("positive", 0),
                    "neutral": sentiment_counts.get("neutral", 0),
                    "negative": sentiment_counts.get("negative", 0),
                },
                "samples": sentiment_samples,
                "comment_count": total_comments,
            },
            "top_users": {"users": top_users[:10]},
            "insights": {"items": insight_items},
            "meta": {
                "room_id": collector.get("room_id", ""),
                "web_rid": collector.get("web_rid", ""),
                "anchor_id": collector.get("anchor_id", ""),
                "anchor_nickname": collector.get("anchor_nickname", ""),
                "status_text": collector.get("status_text", ""),
                "current_online_users": current_online,
                "total_viewers": total_viewers,
                "event_count": len(events),
                "audience_count": len(audience),
                "event_counts": event_counts,
                "updated_at": latest_ts,
            },
        }


_WEB_COLLECTOR_BRIDGE = WebCollectorBridge()


def get_web_collector_bridge() -> WebCollectorBridge:
    return _WEB_COLLECTOR_BRIDGE
