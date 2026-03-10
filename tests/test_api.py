import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "apps" / "backend"))

from app import create_app  # noqa: E402


def test_health():
    app = create_app()
    client = app.test_client()
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_overview():
    app = create_app()
    client = app.test_client()
    resp = client.get("/api/overview/live_001")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["live_id"] == "live_001"
    assert data["online_users"] > 0
