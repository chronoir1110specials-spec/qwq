import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "apps" / "backend"))

from app.sentiment import analyze_text  # noqa: E402


def test_sentiment_positive():
    result = analyze_text("这个真的好，推荐买")
    assert result["label"] == "positive"


def test_sentiment_negative():
    result = analyze_text("太贵了，体验差")
    assert result["label"] == "negative"
