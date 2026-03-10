from .sentiment import analyze_text


def get_overview(conn, live_id: str):
    row = conn.execute(
        """
        SELECT live_id, online_users, likes, gifts, gmv, updated_at
        FROM live_overview
        WHERE live_id = ?
        """,
        (live_id,),
    ).fetchone()
    return dict(row) if row else None


def get_trend(conn, live_id: str, metric: str):
    metric_map = {
        "online_users": "online_users",
        "likes": "likes",
        "gifts": "gifts",
    }
    field = metric_map.get(metric, "online_users")
    rows = conn.execute(
        f"""
        SELECT ts, {field} AS value
        FROM metric_trend
        WHERE live_id = ?
        ORDER BY ts ASC
        """,
        (live_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_heatmap(conn, live_id: str):
    rows = conn.execute(
        """
        SELECT minute_slot, interaction_count
        FROM interaction_heatmap
        WHERE live_id = ?
        ORDER BY minute_slot ASC
        """,
        (live_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_funnel(conn, live_id: str):
    row = conn.execute(
        """
        SELECT exposure, click, add_cart, purchase
        FROM ecommerce_funnel
        WHERE live_id = ?
        """,
        (live_id,),
    ).fetchone()
    return dict(row) if row else None


def get_top_users(conn, live_id: str):
    rows = conn.execute(
        """
        SELECT user_id, comments, likes, gifts, score
        FROM user_interaction
        WHERE live_id = ?
        ORDER BY score DESC
        LIMIT 10
        """,
        (live_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_sentiment_summary(conn, live_id: str):
    rows = conn.execute(
        """
        SELECT content
        FROM danmu
        WHERE live_id = ?
        ORDER BY ts DESC
        LIMIT 200
        """,
        (live_id,),
    ).fetchall()

    summary = {"positive": 0, "negative": 0, "neutral": 0}
    samples = []
    for row in rows:
        text = row["content"]
        analyzed = analyze_text(text)
        summary[analyzed["label"]] += 1
        if len(samples) < 8:
            samples.append({"text": text, "label": analyzed["label"]})

    total = sum(summary.values()) or 1
    ratio = {k: round(v / total, 4) for k, v in summary.items()}
    return {"summary": summary, "ratio": ratio, "samples": samples}
