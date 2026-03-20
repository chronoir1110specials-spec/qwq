"""Headless Douyin Web live collector adapter based on the Tiktok-live workflow."""

from __future__ import annotations

import gzip
import hashlib
import importlib
import importlib.util
import json
import random
import re
import shutil
import string
import subprocess
import sys
import threading
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from collector_common import EventPublisher


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

CORE_RUNTIME_MODULES = {
    "requests": "requests",
    "websocket": "websocket-client",
    "betterproto": "betterproto",
}


def _root_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_web_live_source_dir(source_dir: str = "") -> Path:
    if source_dir:
        return Path(source_dir).expanduser().resolve()
    return (_root_dir() / "爬取" / "Tiktok-live").resolve()


def get_web_live_runtime(source_dir: str = "") -> dict:
    resolved = resolve_web_live_source_dir(source_dir)
    missing_dependencies = [
        pip_name
        for module_name, pip_name in CORE_RUNTIME_MODULES.items()
        if importlib.util.find_spec(module_name) is None
    ]
    signature_engines = []
    if shutil.which("node"):
        signature_engines.append("node")
    if importlib.util.find_spec("py_mini_racer") is not None:
        signature_engines.append("mini-racer")
    if not signature_engines:
        missing_dependencies.append("node or mini-racer")
    required_files = [
        resolved / "sign.js",
        resolved / "protobuf" / "douyin.py",
        resolved / "protobuf" / "__init__.py",
    ]
    missing_files = [str(path) for path in required_files if not path.exists()]
    available = resolved.exists() and not missing_dependencies and not missing_files
    return {
        "available": available,
        "source_dir": str(resolved),
        "missing_dependencies": missing_dependencies,
        "missing_files": missing_files,
        "signature_engines": signature_engines,
    }


def _load_web_live_support(source_dir: str = "") -> tuple[Any, Any, Any, Path]:
    runtime = get_web_live_runtime(source_dir)
    if not runtime["available"]:
        detail = []
        if runtime["missing_dependencies"]:
            detail.append(f"missing dependencies: {', '.join(runtime['missing_dependencies'])}")
        if runtime["missing_files"]:
            detail.append(f"missing files: {', '.join(runtime['missing_files'])}")
        raise RuntimeError("; ".join(detail) or "web live runtime is unavailable")

    import requests  # type: ignore
    import websocket  # type: ignore

    source_path = Path(runtime["source_dir"])
    source_dir_str = str(source_path)
    if source_dir_str not in sys.path:
        sys.path.insert(0, source_dir_str)
        importlib.invalidate_caches()
    proto = importlib.import_module("protobuf.douyin")
    return requests, websocket, proto, source_path


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _truncate_text(value: str, limit: int = 220) -> str:
    raw = str(value or "").replace("\r", " ").replace("\n", " ").strip()
    if len(raw) <= limit:
        return raw
    return raw[:limit] + "..."


def _preview_response_text(response: Any, limit: int = 220) -> str:
    try:
        return _truncate_text(response.text, limit=limit)
    except Exception:
        return ""


def _raise_json_response_error(response: Any, scene: str) -> None:
    content_type = str(response.headers.get("content-type", "")).strip() or "未知类型"
    preview = _preview_response_text(response)
    if not preview:
        raise RuntimeError(
            f"{scene}失败：抖音返回了空响应，预期应为 JSON。HTTP {response.status_code}，Content-Type: {content_type}。"
        )
    raise RuntimeError(
        f"{scene}失败：抖音返回的不是有效 JSON。HTTP {response.status_code}，"
        f"Content-Type: {content_type}，响应片段：{preview}"
    )


def _extract_room_id_from_html(html: str, web_rid: str) -> str:
    text = str(html or "")
    targeted_patterns = [
        rf'\\"roomId\\":\\"(\d+)\\",\\"web_rid\\":\\"{re.escape(web_rid)}\\"',
        rf'\\"web_rid\\":\\"{re.escape(web_rid)}\\".*?\\"roomId\\":\\"(\d+)\\"',
        rf'"roomId":"(\d+)","web_rid":"{re.escape(web_rid)}"',
        rf'"web_rid":"{re.escape(web_rid)}".*?"roomId":"(\d+)"',
    ]
    for pattern in targeted_patterns:
        match = re.search(pattern, text, flags=re.S)
        if match:
            return str(match.group(1))

    fallback_patterns = [
        r'\\"roomId\\":\\"(\d+)\\"',
        r'"roomId":"(\d+)"',
    ]
    for pattern in fallback_patterns:
        matches = re.findall(pattern, text, flags=re.S)
        if matches:
            return str(matches[-1])

    return ""


def _extract_anchor_info_from_html(html: str, web_rid: str) -> dict:
    text = str(html or "")
    patterns = [
        rf'\\"roomId\\":\\"(\d+)\\",\\"web_rid\\":\\"{re.escape(web_rid)}\\",\\"anchor\\":\{{.*?\\"id_str\\":\\"(\d+)\\\".*?\\"nickname\\":\\"([^\\"]+)\\"',
        rf'\\"web_rid\\":\\"{re.escape(web_rid)}\\",\\"anchor\\":\{{.*?\\"id_str\\":\\"(\d+)\\\".*?\\"nickname\\":\\"([^\\"]+)\\"',
        r'\\"anchor\\":\{.*?\\"id_str\\":\\"(\d+)\\\".*?\\"nickname\\":\\"([^\\"]+)\\"',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.S)
        if not match:
            continue
        groups = match.groups()
        if len(groups) == 3:
            room_id, anchor_id, nickname = groups
        else:
            room_id = ""
            anchor_id, nickname = groups
        return {
            "room_id": str(room_id or ""),
            "anchor_user_id": str(anchor_id or ""),
            "anchor_nickname": str(nickname or ""),
        }

    return {
        "room_id": "",
        "anchor_user_id": "",
        "anchor_nickname": "",
    }


def _to_iso_timestamp(value: Any) -> str:
    if value in (None, "", 0):
        return _iso_now()
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return _iso_now()
    if numeric > 10**12:
        numeric /= 1000.0
    return datetime.fromtimestamp(numeric, tz=timezone.utc).isoformat()


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _random_numeric(length: int) -> str:
    alphabet = string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


def generate_ms_token(length: int = 107) -> str:
    alphabet = string.ascii_letters + string.digits + "=_"
    return "".join(random.choice(alphabet) for _ in range(length))


def generate_signature(wss_url: str, source_dir: str = "") -> str:
    runtime = get_web_live_runtime(source_dir)
    if not runtime["available"]:
        detail = []
        if runtime["missing_dependencies"]:
            detail.append(f"missing dependencies: {', '.join(runtime['missing_dependencies'])}")
        if runtime["missing_files"]:
            detail.append(f"missing files: {', '.join(runtime['missing_files'])}")
        raise RuntimeError("; ".join(detail) or "web live runtime is unavailable")

    source_path = Path(runtime["source_dir"])

    params = (
        "live_id,aid,version_code,webcast_sdk_version,"
        "room_id,sub_room_id,sub_channel_id,did_rule,"
        "user_unique_id,device_platform,device_type,ac,"
        "identity"
    ).split(",")
    query_parts = urllib.parse.urlparse(wss_url).query.split("&")
    query_map = {
        part.split("=", 1)[0]: part.split("=", 1)[1] if "=" in part else ""
        for part in query_parts
        if part
    }
    joined = ",".join(f"{item}={query_map.get(item, '')}" for item in params)
    md5_value = hashlib.md5(joined.encode("utf-8")).hexdigest()

    errors = []

    if "node" in runtime.get("signature_engines", []):
        node_script = (
            "const fs=require('fs');"
            "const vm=require('vm');"
            "const args=process.argv;"
            "const signPath=args[args.length-2];"
            "const md5=args[args.length-1];"
            "const code=fs.readFileSync(signPath,'utf8');"
            "const ctx={console};"
            "vm.createContext(ctx);"
            "vm.runInContext(code,ctx);"
            "const result=ctx.get_sign(md5);"
            "if(typeof result!=='string'||!result){throw new Error('empty sign result');}"
            "process.stdout.write(result);"
        )
        try:
            completed = subprocess.run(
                ["node", "-e", node_script, str(source_path / "sign.js"), md5_value],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=20,
            )
            signature = completed.stdout.strip()
            if signature:
                return signature
            errors.append("node returned empty signature")
        except Exception as exc:
            errors.append(f"node engine failed: {exc}")

    if "mini-racer" in runtime.get("signature_engines", []):
        try:
            from py_mini_racer import MiniRacer  # type: ignore

            script = (source_path / "sign.js").read_text(encoding="utf-8")
            ctx = MiniRacer()
            ctx.eval(script)
            signature = str(ctx.call("get_sign", md5_value)).strip()
            if signature:
                return signature
            errors.append("mini-racer returned empty signature")
        except Exception as exc:
            errors.append(f"mini-racer engine failed: {exc}")

    raise RuntimeError("生成 WebSocket 签名失败：" + "；".join(errors))


class DouyinWebLiveCollector:
    def __init__(
        self,
        live_id: str,
        web_rid: str,
        publisher: EventPublisher | None = None,
        *,
        source_dir: str = "",
        log_callback: Callable[[str, str], None] | None = None,
        event_callback: Callable[[dict], None] | None = None,
    ):
        self.live_id = str(live_id or "").strip()
        self.web_rid = str(web_rid or "").strip()
        self.publisher = publisher
        self.source_dir = source_dir
        self.log_callback = log_callback
        self.event_callback = event_callback
        self.user_agent = DEFAULT_USER_AGENT

        self._requests = None
        self._websocket = None
        self._proto = None
        self._source_path: Path | None = None

        self._ttwid: str | None = None
        self._room_id: str | None = None
        self._live_page_html: str = ""
        self._current_online_users = 0
        self._current_total_viewers = 0
        self._latest_status = ""

        self._ws = None
        self._heartbeat_thread: threading.Thread | None = None
        self.running = False

    def _ensure_runtime(self) -> None:
        if self._requests is not None:
            return
        requests, websocket, proto, source_path = _load_web_live_support(self.source_dir)
        self._requests = requests
        self._websocket = websocket
        self._proto = proto
        self._source_path = source_path

    def _log(self, log_type: str, message: str) -> None:
        if self.log_callback is not None:
            self.log_callback(log_type, message)
            return
        print(f"[collector][web-live][{log_type}] {message}")

    def _fetch_live_page_html(self) -> str:
        self._ensure_runtime()
        response = self._requests.get(
            f"https://live.douyin.com/{self.web_rid}",
            headers={
                "User-Agent": self.user_agent,
                "cookie": (
                    f"ttwid={self.ttwid}; "
                    f"msToken={generate_ms_token()}; "
                    "__ac_nonce=0123407cc00a9e438deb4"
                ),
            },
            timeout=15,
        )
        response.raise_for_status()
        self._live_page_html = response.text
        return self._live_page_html

    def _fallback_room_status_from_page(self) -> dict:
        html = self._live_page_html or self._fetch_live_page_html()
        anchor_info = _extract_anchor_info_from_html(html, self.web_rid)
        room_id = self._room_id or anchor_info.get("room_id") or _extract_room_id_from_html(html, self.web_rid)
        if room_id:
            self._room_id = str(room_id)
        return {
            "ok": bool(self._room_id),
            "live_id": self.live_id,
            "web_rid": self.web_rid,
            "room_id": self._room_id or "",
            "room_status": -1,
            "status_text": "网页已打开，状态待确认",
            "anchor_nickname": str(anchor_info.get("anchor_nickname", "")),
            "anchor_user_id": str(anchor_info.get("anchor_user_id", "")),
            "status_source": "page_fallback",
            "raw": {},
        }

    @property
    def ttwid(self) -> str:
        self._ensure_runtime()
        if self._ttwid:
            return self._ttwid
        response = self._requests.get(
            "https://live.douyin.com/",
            headers={"User-Agent": self.user_agent},
            timeout=15,
        )
        response.raise_for_status()
        self._ttwid = str(response.cookies.get("ttwid", "")).strip()
        if not self._ttwid:
            raise RuntimeError("获取 ttwid 失败：抖音首页未返回有效 cookie。")
        return self._ttwid

    @property
    def room_id(self) -> str:
        self._ensure_runtime()
        if self._room_id:
            return self._room_id
        if not self.web_rid:
            raise RuntimeError("web_rid is required")

        html = self._live_page_html or self._fetch_live_page_html()
        self._room_id = _extract_room_id_from_html(html, self.web_rid)
        if not self._room_id:
            preview = _truncate_text(html)
            raise RuntimeError(
                "解析 room_id 失败：当前直播页结构与现有规则不匹配，"
                f"web_rid={self.web_rid}，页面片段：{preview}"
            )
        return self._room_id

    def get_room_status(self) -> dict:
        self._ensure_runtime()
        url = (
            "https://live.douyin.com/webcast/room/web/enter/?aid=6383"
            "&app_name=douyin_web&live_id=1&device_platform=web&language=zh-CN&enter_from=web_live"
            "&cookie_enabled=true&screen_width=1536&screen_height=864&browser_language=zh-CN&browser_platform=Win32"
            "&browser_name=Edge&browser_version=133.0.0.0"
            f"&web_rid={self.web_rid}"
            f"&room_id_str={self.room_id}"
            "&enter_source=&is_need_double_stream=false&insert_task_id=&live_reason="
            "&msToken=&a_bogus="
        )
        response = self._requests.get(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Cookie": f"ttwid={self.ttwid};",
            },
            timeout=15,
        )
        response.raise_for_status()
        try:
            payload = response.json().get("data") or {}
        except ValueError:
            fallback = self._fallback_room_status_from_page()
            self._log(
                "WARN",
                "查询直播状态接口返回空响应，已回退到直播页解析。"
                f" room_id={fallback.get('room_id', '-')}, anchor={fallback.get('anchor_nickname', '-')}",
            )
            return fallback
        if not payload:
            fallback = self._fallback_room_status_from_page()
            self._log(
                "WARN",
                "查询直播状态接口未返回 data 字段，已回退到直播页解析。"
                f" room_id={fallback.get('room_id', '-')}, anchor={fallback.get('anchor_nickname', '-')}",
            )
            return fallback
        user = payload.get("user") or {}
        room_status = _safe_int(payload.get("room_status"), -1)
        status_text = "正在直播" if room_status == 0 else "已结束" if room_status == 2 else "未知"
        self._latest_status = status_text
        return {
            "ok": bool(payload),
            "live_id": self.live_id,
            "web_rid": self.web_rid,
            "room_id": self.room_id,
            "room_status": room_status,
            "status_text": status_text,
            "anchor_nickname": str(user.get("nickname", "")),
            "anchor_user_id": str(user.get("id_str", "")),
            "raw": payload,
        }

    def get_audience_ranklist(self, anchor_id: str) -> list[dict]:
        self._ensure_runtime()
        if not str(anchor_id or "").strip():
            raise RuntimeError("anchor_id is required")
        url = (
            "https://live.douyin.com/webcast/ranklist/audience/"
            f"?aid=6383&app_name=douyin_web&webcast_sdk_version=2450&room_id={self.room_id}"
            f"&anchor_id={anchor_id}&rank_type=30&a_bogus="
        )
        response = self._requests.get(
            url,
            headers={"User-Agent": self.user_agent},
            timeout=15,
        )
        response.raise_for_status()
        try:
            payload = response.json()
        except ValueError:
            _raise_json_response_error(response, "查询观众榜")
        ranks = ((payload.get("data") or {}).get("ranks")) or []
        items = []
        for index, rank in enumerate(ranks, start=1):
            user = rank.get("user") or {}
            items.append(
                {
                    "rank": index,
                    "user_id": str(user.get("id", "")),
                    "nickname": str(user.get("nickname", "")),
                    "display_id": str(user.get("display_id", "")),
                }
            )
        return items

    def start(self) -> None:
        self.running = True
        self._connect_websocket()

    def stop(self) -> None:
        self.running = False
        if self._ws is not None:
            try:
                self._ws.close()
            except Exception:
                pass
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=1.0)

    def _build_wss_url(self) -> str:
        room_id = self.room_id
        now_ms = int(time.time() * 1000)
        did = _random_numeric(19)
        cursor = f"d-1_u-1_fh-{did}_t-{now_ms}_r-1"
        internal_ext = (
            f"internal_src:dim|wss_push_room_id:{room_id}|wss_push_did:{did}"
            f"|first_req_ms:{max(now_ms - 100, 0)}|fetch_time:{now_ms}|seq:1|wss_info:0-{now_ms}-0-0|wrds_v:{did}"
        )
        wss = (
            "wss://webcast100-ws-web-lq.douyin.com/webcast/im/push/v2/?app_name=douyin_web"
            "&version_code=180800&webcast_sdk_version=1.0.14-beta.0"
            "&update_version_code=1.0.14-beta.0&compress=gzip&device_platform=web&cookie_enabled=true"
            "&screen_width=1536&screen_height=864&browser_language=zh-CN&browser_platform=Win32"
            "&browser_name=Mozilla"
            "&browser_version=5.0%20(Windows%20NT%2010.0;%20Win64;%20x64)%20AppleWebKit/537.36%20(KHTML,"
            "%20like%20Gecko)%20Chrome/126.0.0.0%20Safari/537.36"
            "&browser_online=true&tz_name=Asia/Shanghai"
            f"&cursor={cursor}"
            f"&internal_ext={urllib.parse.quote(internal_ext, safe=':|')}"
            "&host=https://live.douyin.com&aid=6383&live_id=1&did_rule=3&endpoint=live_pc&support_wrds=1"
            f"&user_unique_id={did}&im_path=/webcast/im/fetch/&identity=audience"
            f"&need_persist_msg_count=15&insert_task_id=&live_reason=&room_id={room_id}&heartbeatDuration=0"
        )
        signature = generate_signature(wss, self.source_dir)
        return f"{wss}&signature={signature}"

    def _connect_websocket(self) -> None:
        self._ensure_runtime()
        wss = self._build_wss_url()
        headers = {
            "cookie": f"ttwid={self.ttwid}",
            "user-agent": self.user_agent,
        }
        self._log("WEBSOCKET", f"connecting to {wss[:120]}...")
        self._ws = self._websocket.WebSocketApp(
            wss,
            header=headers,
            on_open=self._ws_on_open,
            on_message=self._ws_on_message,
            on_error=self._ws_on_error,
            on_close=self._ws_on_close,
        )
        self._ws.run_forever()

    def _ws_on_open(self, _ws) -> None:
        self._log("WEBSOCKET", "websocket connected")
        self._heartbeat_thread = threading.Thread(target=self._send_heartbeat, daemon=True)
        self._heartbeat_thread.start()

    def _send_heartbeat(self) -> None:
        while self.running:
            try:
                if self._ws and self._ws.sock and self._ws.sock.connected:
                    heartbeat = self._proto.PushFrame(payload_type="hb").SerializeToString()
                    self._ws.send(heartbeat, self._websocket.ABNF.OPCODE_PING)
                else:
                    break
            except Exception as exc:
                self._log("ERROR", f"heartbeat failed: {exc}")
                break
            time.sleep(5)

    def _ws_on_message(self, ws, message: bytes) -> None:
        try:
            package = self._proto.PushFrame().parse(message)
            payload = gzip.decompress(package.payload)
            response = self._proto.Response().parse(payload)
        except Exception as exc:
            self._log("ERROR", f"failed to decode websocket payload: {exc}")
            return

        if response.need_ack:
            try:
                ack = self._proto.PushFrame(
                    log_id=package.log_id,
                    payload_type="ack",
                    payload=response.internal_ext.encode("utf-8"),
                ).SerializeToString()
                ws.send(ack, self._websocket.ABNF.OPCODE_BINARY)
            except Exception as exc:
                self._log("ERROR", f"failed to ack message: {exc}")

        handlers = {
            "WebcastChatMessage": self._parse_chat_message,
            "WebcastGiftMessage": self._parse_gift_message,
            "WebcastLikeMessage": self._parse_like_message,
            "WebcastMemberMessage": self._parse_member_message,
            "WebcastSocialMessage": self._parse_social_message,
            "WebcastRoomUserSeqMessage": self._parse_room_user_seq_message,
            "WebcastFansclubMessage": self._parse_fansclub_message,
            "WebcastEmojiChatMessage": self._parse_emoji_message,
            "WebcastRoomStatsMessage": self._parse_room_stats_message,
            "WebcastRoomMessage": self._parse_room_message,
            "WebcastRoomRankMessage": self._parse_rank_message,
            "WebcastControlMessage": self._parse_control_message,
            "WebcastRoomStreamAdaptationMessage": self._parse_room_stream_message,
        }
        for msg in response.messages_list:
            handler = handlers.get(msg.method)
            if handler is None:
                continue
            try:
                handler(msg.payload)
            except Exception as exc:
                self._log("ERROR", f"failed to parse {msg.method}: {exc}")

    def _ws_on_error(self, _ws, error) -> None:
        self._log("ERROR", f"websocket error: {error}")

    def _ws_on_close(self, _ws, *_args) -> None:
        self.running = False
        self._log("WEBSOCKET", "websocket closed")

    def _emit_event(
        self,
        event_type: str,
        *,
        event_time: Any = None,
        user_id: Any = "",
        user_name: str = "",
        comment: str = "",
        like_count: int = 0,
        gift_value: float = 0.0,
        online_users: int | None = None,
        **extra: Any,
    ) -> dict:
        payload = {
            "event_time": _to_iso_timestamp(event_time),
            "live_id": self.live_id,
            "web_rid": self.web_rid,
            "room_id": self._room_id or "",
            "source": "douyin_web_live",
            "user_id": str(user_id or ""),
            "user_name": str(user_name or ""),
            "event_type": event_type,
            "online_users": _safe_int(self._current_online_users if online_users is None else online_users),
            "like_count": _safe_int(like_count),
            "gift_value": round(_safe_float(gift_value), 2),
            "product_id": "",
            "product_action": "",
            "comment": str(comment or ""),
        }
        for key, value in extra.items():
            payload[key] = value
        if self.publisher is not None:
            self.publisher.publish(payload)
        if self.event_callback is not None:
            self.event_callback(payload)
        return payload

    def _parse_chat_message(self, payload: bytes) -> None:
        message = self._proto.ChatMessage().parse(payload)
        user_id = message.user.id_str or message.user.id or message.user.sec_uid
        self._emit_event(
            "comment",
            event_time=message.event_time or message.common.create_time,
            user_id=user_id,
            user_name=message.user.nick_name,
            comment=message.content,
        )
        self._log("CHAT", f"[{user_id}]{message.user.nick_name}: {message.content}")

    def _parse_gift_message(self, payload: bytes) -> None:
        message = self._proto.GiftMessage().parse(payload)
        user_id = message.user.id_str or message.user.id or message.user.sec_uid
        gift_count = max(
            1,
            _safe_int(message.combo_count),
            _safe_int(message.repeat_count),
            _safe_int(message.group_count),
            _safe_int(message.total_count),
        )
        gift_unit_value = _safe_float(message.gift.diamond_count)
        gift_value = gift_unit_value * gift_count
        self._emit_event(
            "gift",
            event_time=message.send_time or message.common.create_time,
            user_id=user_id,
            user_name=message.user.nick_name,
            gift_value=gift_value,
            gift_name=message.gift.name,
            gift_count=gift_count,
        )
        self._log("GIFT", f"{message.user.nick_name} sent {message.gift.name} x{gift_count}")

    def _parse_like_message(self, payload: bytes) -> None:
        message = self._proto.LikeMessage().parse(payload)
        user_id = message.user.id_str or message.user.id or message.user.sec_uid
        self._emit_event(
            "like",
            event_time=message.common.create_time,
            user_id=user_id,
            user_name=message.user.nick_name,
            like_count=_safe_int(message.count, 1),
            like_total=_safe_int(message.total),
        )
        self._log("LIKE", f"{message.user.nick_name} liked x{message.count}")

    def _parse_member_message(self, payload: bytes) -> None:
        message = self._proto.MemberMessage().parse(payload)
        user_id = message.user.id_str or message.user.id or message.user.sec_uid or message.user_id
        self._emit_event(
            "enter",
            event_time=message.common.create_time,
            user_id=user_id,
            user_name=message.user.nick_name,
            member_count=_safe_int(message.member_count),
            action_description=message.action_description,
        )
        self._log("ENTER", f"[{user_id}]{message.user.nick_name} entered the room")

    def _parse_social_message(self, payload: bytes) -> None:
        message = self._proto.SocialMessage().parse(payload)
        user_id = message.user.id_str or message.user.id or message.user.sec_uid
        self._emit_event(
            "follow",
            event_time=message.common.create_time,
            user_id=user_id,
            user_name=message.user.nick_name,
            follow_count=_safe_int(message.follow_count),
        )
        self._log("FOLLOW", f"[{user_id}]{message.user.nick_name} followed the streamer")

    def _parse_room_user_seq_message(self, payload: bytes) -> None:
        message = self._proto.RoomUserSeqMessage().parse(payload)
        self._current_online_users = max(
            _safe_int(message.total),
            _safe_int(message.total_user),
            _safe_int(message.online_user_for_anchor),
        )
        self._current_total_viewers = max(
            _safe_int(message.total_pv_for_anchor),
            _safe_int(message.total_str),
            self._current_total_viewers,
        )
        self._emit_event(
            "room_stats",
            event_time=message.common.create_time,
            online_users=self._current_online_users,
            total_viewers=self._current_total_viewers,
        )
        self._log(
            "STATS",
            f"online_users={self._current_online_users}, total_viewers={self._current_total_viewers}",
        )

    def _parse_fansclub_message(self, payload: bytes) -> None:
        message = self._proto.FansclubMessage().parse(payload)
        user_id = message.user.id_str or message.user.id or message.user.sec_uid
        self._emit_event(
            "fansclub",
            event_time=message.common_info.create_time,
            user_id=user_id,
            user_name=message.user.nick_name,
            comment=message.content,
            fansclub_type=_safe_int(message.type),
        )
        self._log("FANSCLUB", message.content)

    def _parse_emoji_message(self, payload: bytes) -> None:
        message = self._proto.EmojiChatMessage().parse(payload)
        user_id = message.user.id_str or message.user.id or message.user.sec_uid
        self._emit_event(
            "emoji",
            event_time=message.common.create_time,
            user_id=user_id,
            user_name=message.user.nick_name,
            comment=message.default_content,
            emoji_id=_safe_int(message.emoji_id),
        )
        self._log("EMOJI", f"[{user_id}]{message.user.nick_name}: {message.default_content}")

    def _parse_room_message(self, payload: bytes) -> None:
        message = self._proto.RoomMessage().parse(payload)
        self._emit_event(
            "room_message",
            event_time=message.common.create_time,
            comment=message.content,
            room_message_type=str(message.roommessagetype),
        )
        self._log("ROOM", message.content or f"room_id={message.common.room_id}")

    def _parse_room_stats_message(self, payload: bytes) -> None:
        message = self._proto.RoomStatsMessage().parse(payload)
        candidate_online = max(_safe_int(message.display_value), _safe_int(message.total))
        if candidate_online > 0:
            self._current_online_users = candidate_online
        self._emit_event(
            "room_stats",
            event_time=message.common.create_time,
            online_users=self._current_online_users,
            total_viewers=max(self._current_total_viewers, _safe_int(message.total)),
            stats_text=message.display_long,
        )
        self._log("STATS", message.display_long or f"online_users={self._current_online_users}")

    def _parse_rank_message(self, payload: bytes) -> None:
        message = self._proto.RoomRankMessage().parse(payload)
        ranks = []
        for index, item in enumerate(message.ranks_list, start=1):
            user = item.user
            ranks.append(
                {
                    "rank": index,
                    "user_id": str(user.id_str or user.id or user.sec_uid),
                    "nickname": user.nick_name,
                    "score": item.score_str,
                }
            )
        self._emit_event("rank_snapshot", ranks=ranks[:10])
        self._log("RANK", f"received {len(ranks)} rank items")

    def _parse_control_message(self, payload: bytes) -> None:
        message = self._proto.ControlMessage().parse(payload)
        status_code = _safe_int(message.status)
        if status_code == 3:
            self._latest_status = "已结束"
        self._emit_event("room_control", event_time=message.common.create_time, status_code=status_code)
        self._log("STATUS", f"room status code={status_code}")
        if status_code == 3:
            self.stop()

    def _parse_room_stream_message(self, payload: bytes) -> None:
        message = self._proto.RoomStreamAdaptationMessage().parse(payload)
        self._emit_event(
            "stream_adaptation",
            event_time=message.common.create_time,
            adaptation_type=_safe_int(message.adaptation_type),
        )
        self._log("ADAPTATION", f"adaptation_type={message.adaptation_type}")


def inspect_web_live_room(web_rid: str, *, live_id: str = "web_live_probe", source_dir: str = "") -> dict:
    collector = DouyinWebLiveCollector(live_id=live_id, web_rid=web_rid, source_dir=source_dir)
    return collector.get_room_status()


def inspect_web_live_audience(
    web_rid: str,
    anchor_id: str,
    *,
    live_id: str = "web_live_probe",
    source_dir: str = "",
) -> list[dict]:
    collector = DouyinWebLiveCollector(live_id=live_id, web_rid=web_rid, source_dir=source_dir)
    return collector.get_audience_ranklist(anchor_id)


def run_web_live(
    publisher: EventPublisher,
    *,
    live_id: str,
    web_rid: str,
    source_dir: str = "",
    log_callback: Callable[[str, str], None] | None = None,
    event_callback: Callable[[dict], None] | None = None,
) -> None:
    collector = DouyinWebLiveCollector(
        live_id=live_id,
        web_rid=web_rid,
        publisher=publisher,
        source_dir=source_dir,
        log_callback=log_callback,
        event_callback=event_callback,
    )
    collector.start()
