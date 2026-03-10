CATALOG = {
    "beauty": [
        {"product_id": "p1001", "name": "水润精华液"},
        {"product_id": "p1002", "name": "保湿修护面膜"},
    ],
    "food": [
        {"product_id": "p2001", "name": "低糖零食组合"},
        {"product_id": "p2002", "name": "即食燕麦早餐杯"},
    ],
    "digital": [
        {"product_id": "p3001", "name": "降噪蓝牙耳机"},
        {"product_id": "p3002", "name": "便携移动电源"},
    ],
}

CATEGORY_CN = {
    "beauty": "美妆个护",
    "food": "食品饮料",
    "digital": "数码配件",
}


def recommend_for_user(conn, user_id: str, top_n: int = 5) -> list:
    rows = conn.execute(
        """
        SELECT category, score
        FROM user_interest
        WHERE user_id = ?
        ORDER BY score DESC
        LIMIT 3
        """,
        (user_id,),
    ).fetchall()

    recommendations = []
    seen = set()
    for row in rows:
        category = row["category"]
        for product in CATALOG.get(category, []):
            pid = product["product_id"]
            if pid in seen:
                continue
            seen.add(pid)
            recommendations.append(
                {
                    "product_id": pid,
                    "name": product["name"],
                    "reason": f"兴趣匹配:{CATEGORY_CN.get(category, category)}",
                    "score": round(float(row["score"]), 4),
                }
            )
            if len(recommendations) >= top_n:
                return recommendations
    return recommendations
