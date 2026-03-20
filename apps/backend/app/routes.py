import json
import time

from flask import Blueprint, Response, jsonify, request, stream_with_context

from .analytics import (
    get_funnel,
    get_heatmap,
    get_overview,
    get_sentiment_summary,
    get_top_users,
    get_trend,
)
from .db import get_connection
from .realtime_store import get_realtime_store
from .recommend import recommend_for_user
from .seed import init_and_seed
from .web_collector import get_web_collector_bridge


api_bp = Blueprint("api", __name__)


@api_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@api_bp.route("/bootstrap", methods=["POST"])
def bootstrap():
    init_and_seed(force=True)
    return jsonify({"ok": True, "message": "database bootstrapped"})


@api_bp.route("/overview/<live_id>", methods=["GET"])
def overview(live_id: str):
    with get_connection() as conn:
        data = get_overview(conn, live_id)
    if not data:
        return jsonify({"error": "live not found"}), 404
    return jsonify(data)


@api_bp.route("/trend/<live_id>", methods=["GET"])
def trend(live_id: str):
    metric = request.args.get("metric", "online_users")
    with get_connection() as conn:
        data = get_trend(conn, live_id, metric)
    return jsonify({"live_id": live_id, "metric": metric, "points": data})


@api_bp.route("/heatmap/<live_id>", methods=["GET"])
def heatmap(live_id: str):
    with get_connection() as conn:
        data = get_heatmap(conn, live_id)
    return jsonify({"live_id": live_id, "items": data})


@api_bp.route("/funnel/<live_id>", methods=["GET"])
def funnel(live_id: str):
    with get_connection() as conn:
        data = get_funnel(conn, live_id)
    if not data:
        return jsonify({"error": "funnel not found"}), 404
    return jsonify({"live_id": live_id, "funnel": data})


@api_bp.route("/interaction/top-users/<live_id>", methods=["GET"])
def top_users(live_id: str):
    with get_connection() as conn:
        data = get_top_users(conn, live_id)
    return jsonify({"live_id": live_id, "users": data})


@api_bp.route("/sentiment/<live_id>", methods=["GET"])
def sentiment(live_id: str):
    with get_connection() as conn:
        data = get_sentiment_summary(conn, live_id)
    return jsonify({"live_id": live_id, **data})


@api_bp.route("/recommend/<user_id>", methods=["GET"])
def recommend(user_id: str):
    top_n = int(request.args.get("top_n", "5"))
    with get_connection() as conn:
        items = recommend_for_user(conn, user_id, top_n=top_n)
    return jsonify({"user_id": user_id, "items": items})


@api_bp.route("/panorama/compare", methods=["GET"])
def compare():
    ids = request.args.get("live_ids", "")
    live_ids = [i.strip() for i in ids.split(",") if i.strip()]
    result = []
    with get_connection() as conn:
        for lid in live_ids:
            overview_data = get_overview(conn, lid)
            if overview_data:
                result.append(overview_data)
    return jsonify({"items": result})


@api_bp.route("/realtime/<live_id>", methods=["GET"])
def realtime_snapshot(live_id: str):
    limit = max(1, min(int(request.args.get("limit", "60")), 500))
    store = get_realtime_store()
    store.ensure_started()
    return jsonify(store.get_snapshot(live_id, limit=limit))


@api_bp.route("/realtime/stream/<live_id>", methods=["GET"])
def realtime_stream(live_id: str):
    interval = max(0.5, min(float(request.args.get("interval", "1.0")), 10.0))
    limit = max(1, min(int(request.args.get("limit", "60")), 500))
    store = get_realtime_store()
    store.ensure_started()

    @stream_with_context
    def event_stream():
        while True:
            payload = store.get_snapshot(live_id, limit=limit)
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            time.sleep(interval)

    return Response(event_stream(), mimetype="text/event-stream")


@api_bp.route("/collector/web/snapshot", methods=["GET"])
def web_collector_snapshot():
    bridge = get_web_collector_bridge()
    limit_events = max(1, min(int(request.args.get("limit_events", "20")), 80))
    limit_logs = max(1, min(int(request.args.get("limit_logs", "30")), 120))
    return jsonify(bridge.snapshot(limit_events=limit_events, limit_logs=limit_logs))


@api_bp.route("/collector/web/analytics/<live_id>", methods=["GET"])
def web_collector_analytics(live_id: str):
    bridge = get_web_collector_bridge()
    max_points = max(6, min(int(request.args.get("limit", "30")), 120))
    data = bridge.analytics(live_id=live_id, max_points=max_points)
    if not data:
        return jsonify({"error": "collector analytics not available"}), 404
    return jsonify(data)


@api_bp.route("/collector/web/inspect", methods=["GET"])
def web_collector_inspect():
    bridge = get_web_collector_bridge()
    live_id = request.args.get("live_id", "live_001").strip() or "live_001"
    web_rid = request.args.get("web_rid", "").strip()
    if not web_rid:
        return jsonify({"ok": False, "error": "web_rid is required"}), 400
    try:
        room_info = bridge.inspect_room(live_id=live_id, web_rid=web_rid)
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc), "snapshot": bridge.snapshot()}), 503
    return jsonify({"ok": True, "room": room_info, "snapshot": bridge.snapshot()})


@api_bp.route("/collector/web/audience", methods=["GET"])
def web_collector_audience():
    bridge = get_web_collector_bridge()
    live_id = request.args.get("live_id", "live_001").strip() or "live_001"
    web_rid = request.args.get("web_rid", "").strip()
    anchor_id = request.args.get("anchor_id", "").strip()
    if not web_rid or not anchor_id:
        return jsonify({"ok": False, "error": "web_rid and anchor_id are required"}), 400
    try:
        audience = bridge.inspect_audience(live_id=live_id, web_rid=web_rid, anchor_id=anchor_id)
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc), "snapshot": bridge.snapshot()}), 503
    return jsonify({"ok": True, "items": audience, "snapshot": bridge.snapshot()})


@api_bp.route("/collector/web/start", methods=["POST"])
def web_collector_start():
    bridge = get_web_collector_bridge()
    payload = request.get_json(silent=True) or {}
    live_id = str(payload.get("live_id", "live_001")).strip() or "live_001"
    web_rid = str(payload.get("web_rid", "")).strip()
    anchor_id = str(payload.get("anchor_id", "")).strip()
    if not web_rid:
        return jsonify({"ok": False, "error": "web_rid is required"}), 400
    result = bridge.start(live_id=live_id, web_rid=web_rid, anchor_id=anchor_id)
    if not result.get("ok"):
        return jsonify(result), 503
    return jsonify(result)


@api_bp.route("/collector/web/stop", methods=["POST"])
def web_collector_stop():
    bridge = get_web_collector_bridge()
    return jsonify(bridge.stop())
