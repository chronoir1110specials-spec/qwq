import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "services" / "collector"))

from collector_web_live import (  # noqa: E402
    DouyinWebLiveCollector,
    _extract_anchor_info_from_html,
    _extract_room_id_from_html,
)


HTML_SNIPPET = (
    'xxx \\"roomId\\":\\"7619136241648388899\\",\\"web_rid\\":\\"544590831076\\",'
    '\\"anchor\\":{\\"id_str\\":\\"138960285477659\\",\\"nickname\\":\\"乱斗教授\\"} yyy'
)


def test_extract_room_id_from_current_page_shape():
    room_id = _extract_room_id_from_html(HTML_SNIPPET, "544590831076")

    assert room_id == "7619136241648388899"


def test_fallback_room_status_from_page_parses_anchor():
    collector = DouyinWebLiveCollector(live_id="live_001", web_rid="544590831076")
    collector._live_page_html = HTML_SNIPPET
    collector._room_id = _extract_room_id_from_html(HTML_SNIPPET, "544590831076")

    room = collector._fallback_room_status_from_page()

    assert room["ok"] is True
    assert room["room_id"] == "7619136241648388899"
    assert room["anchor_user_id"] == "138960285477659"
    assert room["anchor_nickname"] == "乱斗教授"
    assert room["status_text"] == "网页已打开，状态待确认"


def test_extract_anchor_info_from_current_page_shape():
    anchor = _extract_anchor_info_from_html(HTML_SNIPPET, "544590831076")

    assert anchor == {
        "room_id": "7619136241648388899",
        "anchor_user_id": "138960285477659",
        "anchor_nickname": "乱斗教授",
    }
