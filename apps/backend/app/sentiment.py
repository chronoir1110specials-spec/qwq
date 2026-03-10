POSITIVE_WORDS = {
    "好",
    "喜欢",
    "赞",
    "棒",
    "冲",
    "买",
    "值",
    "开心",
    "支持",
    "推荐",
}

NEGATIVE_WORDS = {
    "差",
    "坑",
    "贵",
    "垃圾",
    "失望",
    "退",
    "不行",
    "骗",
    "慢",
    "卡",
}


def analyze_text(text: str) -> dict:
    raw = (text or "").strip().lower()
    if not raw:
        return {"label": "neutral", "score": 0}

    pos = sum(1 for w in POSITIVE_WORDS if w in raw)
    neg = sum(1 for w in NEGATIVE_WORDS if w in raw)
    score = pos - neg

    if score > 0:
        label = "positive"
    elif score < 0:
        label = "negative"
    else:
        label = "neutral"
    return {"label": label, "score": score}
