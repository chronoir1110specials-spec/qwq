import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "services" / "collector"))

import collector_web_live as web_live  # noqa: E402
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


def test_runtime_disables_broken_mini_racer(monkeypatch, tmp_path):
    (tmp_path / "protobuf").mkdir()
    (tmp_path / "sign.js").write_text("function get_sign(){return 'ok';}", encoding="utf-8")
    (tmp_path / "protobuf" / "douyin.py").write_text("", encoding="utf-8")
    (tmp_path / "protobuf" / "__init__.py").write_text("", encoding="utf-8")

    real_find_spec = web_live.importlib.util.find_spec

    def fake_find_spec(name):
        if name == "py_mini_racer":
            return SimpleNamespace(origin=str(tmp_path / "broken_mini_racer" / "__init__.py"))
        return real_find_spec(name)

    monkeypatch.setattr(web_live.importlib.util, "find_spec", fake_find_spec)
    monkeypatch.setattr(web_live.shutil, "which", lambda _name: None)

    runtime = web_live.get_web_live_runtime(str(tmp_path))

    assert runtime["available"] is False
    assert runtime["signature_engines"] == []
    assert runtime["signature_warnings"] == [
        "py_mini_racer missing runtime files: snapshot_blob.bin, icudtl.dat, mini_racer.dll"
    ]
    assert runtime["missing_dependencies"] == [
        "node.js (mini-racer unavailable: py_mini_racer missing runtime files: snapshot_blob.bin, icudtl.dat, mini_racer.dll)"
    ]
