"""Official push adapter skeleton for Douyin live interaction events."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

from collector_common import EventPublisher


@dataclass
class LiveRoomBinding:
    live_id: str
    room_id: str = ""
    anchor_id: str = ""
    anchor_open_id: str = ""
    account: str = ""


@dataclass
class OfficialPushSettings:
    bind_host: str
    bind_port: int
    webhook_path: str
    verification_token: str
    bindings: list[LiveRoomBinding]


def _nested_get(data: Any, path: str):
    current = data
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
            continue
        if isinstance(current, list) and part.isdigit():
            index = int(part)
            if 0 <= index < len(current):
                current = current[index]
                continue
        return None
    return current


def _first_non_empty(data: Any, paths: list[str], default: Any = None):
    for path in paths:
        value = _nested_get(data, path)
        if value not in (None, "", []):
            return value
    return default


def _iter_candidate_records(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []

    for path in [
        "events",
        "items",
        "records",
        "messages",
        "data.events",
        "data.items",
        "data.records",
        "data.messages",
    ]:
        value = _nested_get(payload, path)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return [payload]


def _normalize_event_type(raw_type: Any) -> str:
    value = str(raw_type or "").strip().lower()
    mapping = {
        "comment": "comment",
        "chat": "comment",
        "danmu": "comment",
        "text": "comment",
        "like": "like",
        "digg": "like",
        "thumb_up": "like",
        "gift": "gift",
        "send_gift": "gift",
        "member": "enter",
        "enter": "enter",
        "join": "enter",
        "leave": "leave",
        "exit": "leave",
        "product_click": "product_click",
        "click": "product_click",
        "purchase": "purchase",
        "pay": "purchase",
    }
    return mapping.get(value, value or "interaction")


def _to_number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def load_official_push_settings(
    config_path: str,
    fallback_live_id: str,
    host: str,
    port: int,
    webhook_path: str,
    verification_token: str,
) -> OfficialPushSettings:
    raw = {}
    if config_path:
        config_file = Path(config_path)
        if config_file.exists():
            if yaml is None:
                raise RuntimeError("pyyaml is required when using --config")
            raw = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}

    official = raw.get("official_push", raw)
    bindings = [
        LiveRoomBinding(
            live_id=str(item.get("live_id", fallback_live_id)).strip() or fallback_live_id,
            room_id=str(item.get("room_id", "")).strip(),
            anchor_id=str(item.get("anchor_id", "")).strip(),
            anchor_open_id=str(item.get("anchor_open_id", "")).strip(),
            account=str(item.get("account", "")).strip(),
        )
        for item in official.get("bindings", [])
        if isinstance(item, dict)
    ]
    if not bindings:
        bindings = [LiveRoomBinding(live_id=fallback_live_id)]

    return OfficialPushSettings(
        bind_host=str(official.get("bind_host", host)),
        bind_port=int(official.get("bind_port", port)),
        webhook_path=str(official.get("webhook_path", webhook_path)),
        verification_token=str(official.get("verification_token", verification_token)),
        bindings=bindings,
    )


class OfficialPayloadAdapter:
    def __init__(self, settings: OfficialPushSettings):
        self.settings = settings

    def _match_binding(self, payload: dict, record: dict) -> LiveRoomBinding:
        room_id = str(
            _first_non_empty(
                record,
                [
                    "room_id",
                    "roomId",
                    "data.room_id",
                    "room.id",
                ],
                default=_first_non_empty(payload, ["room_id", "roomId", "data.room_id", "room.id"], ""),
            )
        ).strip()
        anchor_id = str(
            _first_non_empty(
                record,
                ["anchor_id", "anchorId", "anchor.id"],
                default=_first_non_empty(payload, ["anchor_id", "anchorId", "anchor.id"], ""),
            )
        ).strip()
        anchor_open_id = str(
            _first_non_empty(
                record,
                ["anchor_open_id", "anchorOpenId", "anchor.open_id", "anchor.openId"],
                default=_first_non_empty(
                    payload,
                    ["anchor_open_id", "anchorOpenId", "anchor.open_id", "anchor.openId"],
                    "",
                ),
            )
        ).strip()
        account = str(
            _first_non_empty(
                record,
                ["account", "anchor_account"],
                default=_first_non_empty(payload, ["account", "anchor_account"], ""),
            )
        ).strip()

        for binding in self.settings.bindings:
            if binding.room_id and binding.room_id == room_id:
                return binding
            if binding.anchor_id and binding.anchor_id == anchor_id:
                return binding
            if binding.anchor_open_id and binding.anchor_open_id == anchor_open_id:
                return binding
            if binding.account and binding.account == account:
                return binding
        return self.settings.bindings[0]

    def normalize(self, payload: Any) -> list[dict]:
        records = _iter_candidate_records(payload)
        events: list[dict] = []
        payload_dict = payload if isinstance(payload, dict) else {}
        for record in records:
            binding = self._match_binding(payload_dict, record)
            raw_event_type = _first_non_empty(
                record,
                ["event_type", "msg_type", "type", "message_type", "event.name"],
                default=_first_non_empty(payload_dict, ["event_type", "msg_type", "type"], "interaction"),
            )
            event_type = _normalize_event_type(raw_event_type)
            event_time = _first_non_empty(
                record,
                ["event_time", "ts", "timestamp", "create_time", "message_time"],
                default=_first_non_empty(
                    payload_dict,
                    ["event_time", "ts", "timestamp", "create_time"],
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

            event = {
                "event_time": str(event_time),
                "live_id": binding.live_id,
                "user_id": str(
                    _first_non_empty(
                        record,
                        [
                            "user_id",
                            "user.id",
                            "sec_user_id",
                            "from_user_id",
                            "author_id",
                        ],
                        default="anonymous",
                    )
                ),
                "event_type": event_type,
                "online_users": int(
                    _to_number(
                        _first_non_empty(
                            record,
                            ["online_users", "room_user_count", "room.online_user_count"],
                            default=_first_non_empty(
                                payload_dict,
                                ["online_users", "room_user_count", "room.online_user_count"],
                                0,
                            ),
                        ),
                        0,
                    )
                ),
                "like_count": int(
                    _to_number(
                        _first_non_empty(
                            record,
                            ["like_count", "digg_count", "count"],
                            default=1 if event_type == "like" else 0,
                        ),
                        0,
                    )
                ),
                "gift_value": round(
                    _to_number(
                        _first_non_empty(
                            record,
                            ["gift_value", "amount", "diamond_count", "gift.price"],
                            default=0.0,
                        ),
                        0.0,
                    ),
                    2,
                ),
                "product_id": str(
                    _first_non_empty(
                        record,
                        ["product_id", "goods_id", "item_id", "sku_id"],
                        default="",
                    )
                ),
                "product_action": str(
                    _first_non_empty(
                        record,
                        ["product_action", "goods_action", "action"],
                        default=event_type if event_type in ("product_click", "purchase") else "",
                    )
                ),
                "comment": str(
                    _first_non_empty(
                        record,
                        ["comment", "content", "text", "message"],
                        default="",
                    )
                ),
            }
            events.append(event)
        return events


class OfficialPushRequestHandler(BaseHTTPRequestHandler):
    adapter: OfficialPayloadAdapter | None = None
    publisher: EventPublisher | None = None
    webhook_path = "/webhook/douyin/live"
    verification_token = ""

    def _send_json(self, code: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _verify_token(self) -> bool:
        if not self.verification_token:
            return True
        parsed = urlparse(self.path)
        query_token = parse_qs(parsed.query).get("token", [""])[0]
        header_token = self.headers.get("X-Collector-Token", "")
        return query_token == self.verification_token or header_token == self.verification_token

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != self.webhook_path:
            self._send_json(404, {"ok": False, "message": "not found"})
            return
        self._send_json(200, {"ok": True, "message": "collector webhook ready"})

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != self.webhook_path:
            self._send_json(404, {"ok": False, "message": "not found"})
            return
        if not self._verify_token():
            self._send_json(403, {"ok": False, "message": "invalid token"})
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length > 0 else b""
        try:
            payload = json.loads(raw_body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send_json(400, {"ok": False, "message": "invalid json"})
            return

        if self.adapter is None or self.publisher is None:
            self._send_json(500, {"ok": False, "message": "collector not initialized"})
            return

        events = self.adapter.normalize(payload)
        count = self.publisher.publish_many(events)
        print(f"[collector] official push received, normalized_events={count}")
        self._send_json(200, {"ok": True, "events": count})

    def log_message(self, _format, *args):
        print("[collector] webhook", *args)


def run_official_push_server(
    publisher: EventPublisher,
    config_path: str,
    fallback_live_id: str,
    host: str,
    port: int,
    webhook_path: str,
    verification_token: str,
):
    settings = load_official_push_settings(
        config_path=config_path,
        fallback_live_id=fallback_live_id,
        host=host,
        port=port,
        webhook_path=webhook_path,
        verification_token=verification_token,
    )
    adapter = OfficialPayloadAdapter(settings)

    handler_cls = OfficialPushRequestHandler
    handler_cls.adapter = adapter
    handler_cls.publisher = publisher
    handler_cls.webhook_path = settings.webhook_path
    handler_cls.verification_token = settings.verification_token

    server = ThreadingHTTPServer((settings.bind_host, settings.bind_port), handler_cls)
    print(
        "[collector] official push skeleton ready "
        f"host={settings.bind_host} port={settings.bind_port} path={settings.webhook_path}"
    )
    for binding in settings.bindings:
        print(
            "[collector] binding "
            f"live_id={binding.live_id} room_id={binding.room_id or '-'} "
            f"anchor_id={binding.anchor_id or '-'} anchor_open_id={binding.anchor_open_id or '-'}"
        )
    print("[collector] waiting for official push payloads...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[collector] official push server stopped")
    finally:
        server.server_close()
