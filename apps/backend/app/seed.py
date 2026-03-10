import random
from datetime import datetime, timedelta

from .db import get_connection


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS live_overview (
  live_id TEXT PRIMARY KEY,
  online_users INTEGER NOT NULL,
  likes INTEGER NOT NULL,
  gifts INTEGER NOT NULL,
  gmv REAL NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS metric_trend (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  live_id TEXT NOT NULL,
  ts TEXT NOT NULL,
  online_users INTEGER NOT NULL,
  likes INTEGER NOT NULL,
  gifts INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS interaction_heatmap (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  live_id TEXT NOT NULL,
  minute_slot INTEGER NOT NULL,
  interaction_count INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS ecommerce_funnel (
  live_id TEXT PRIMARY KEY,
  exposure INTEGER NOT NULL,
  click INTEGER NOT NULL,
  add_cart INTEGER NOT NULL,
  purchase INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS danmu (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  live_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  content TEXT NOT NULL,
  ts TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_interest (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  category TEXT NOT NULL,
  score REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS user_interaction (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  live_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  comments INTEGER NOT NULL,
  likes INTEGER NOT NULL,
  gifts INTEGER NOT NULL,
  score REAL NOT NULL
);
"""


DANMU_POOL = [
    "这个产品好，真的喜欢",
    "价格有点贵",
    "主播讲得很棒",
    "物流慢不慢啊",
    "冲冲冲，买它",
    "有点失望，质量一般",
    "支持主播，推荐推荐",
    "卡了，画面不太行",
]


def _seed_overview(conn, now: datetime):
    records = [
        ("live_001", 12450, 365000, 8900, 238900.0, now.isoformat()),
        ("live_002", 8560, 221000, 4200, 168500.0, now.isoformat()),
        ("live_003", 6420, 140500, 2600, 99000.0, now.isoformat()),
    ]
    conn.executemany(
        """
        INSERT INTO live_overview (live_id, online_users, likes, gifts, gmv, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        records,
    )


def _seed_trend(conn, rng: random.Random, base: datetime):
    rows = []
    for live_id, base_online, base_like, base_gift in [
        ("live_001", 12000, 5000, 120),
        ("live_002", 8600, 3200, 90),
        ("live_003", 6400, 2200, 75),
    ]:
        likes_acc = 0
        gifts_acc = 0
        for i in range(60):
            ts = (base + timedelta(minutes=i)).isoformat()
            online_users = max(100, base_online + rng.randint(-1200, 1300))
            likes_inc = max(0, base_like + rng.randint(-1000, 1500))
            gifts_inc = max(0, base_gift + rng.randint(-30, 35))
            likes_acc += likes_inc
            gifts_acc += gifts_inc
            rows.append((live_id, ts, online_users, likes_acc, gifts_acc))
    conn.executemany(
        """
        INSERT INTO metric_trend (live_id, ts, online_users, likes, gifts)
        VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )


def _seed_heatmap(conn, rng: random.Random):
    rows = []
    for live_id, peak in [("live_001", 180), ("live_002", 130), ("live_003", 90)]:
        for m in range(60):
            valley = 0.6 if m < 10 or m > 50 else 1.0
            count = int(max(5, peak * valley + rng.randint(-25, 30)))
            rows.append((live_id, m, count))
    conn.executemany(
        """
        INSERT INTO interaction_heatmap (live_id, minute_slot, interaction_count)
        VALUES (?, ?, ?)
        """,
        rows,
    )


def _seed_funnel(conn):
    rows = [
        ("live_001", 120000, 35000, 14000, 6200),
        ("live_002", 95000, 25000, 9800, 4100),
        ("live_003", 70000, 16000, 6200, 2500),
    ]
    conn.executemany(
        """
        INSERT INTO ecommerce_funnel (live_id, exposure, click, add_cart, purchase)
        VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )


def _seed_danmu(conn, rng: random.Random, base: datetime):
    rows = []
    users = [f"u{i:04d}" for i in range(1, 121)]
    for live_id in ["live_001", "live_002", "live_003"]:
        for i in range(300):
            ts = (base + timedelta(seconds=i * 10)).isoformat()
            rows.append((live_id, rng.choice(users), rng.choice(DANMU_POOL), ts))
    conn.executemany(
        """
        INSERT INTO danmu (live_id, user_id, content, ts)
        VALUES (?, ?, ?, ?)
        """,
        rows,
    )


def _seed_user_interest(conn, rng: random.Random):
    categories = ["beauty", "food", "digital"]
    rows = []
    for uid in [f"u{i:04d}" for i in range(1, 31)]:
        for c in categories:
            rows.append((uid, c, round(rng.uniform(0.1, 1.0), 4)))
    conn.executemany(
        """
        INSERT INTO user_interest (user_id, category, score)
        VALUES (?, ?, ?)
        """,
        rows,
    )


def _seed_user_interaction(conn, rng: random.Random):
    rows = []
    for live_id in ["live_001", "live_002", "live_003"]:
        for uid in [f"u{i:04d}" for i in range(1, 61)]:
            comments = rng.randint(0, 25)
            likes = rng.randint(0, 50)
            gifts = rng.randint(0, 8)
            score = round(comments * 0.3 + likes * 0.2 + gifts * 2.2, 2)
            rows.append((live_id, uid, comments, likes, gifts, score))
    conn.executemany(
        """
        INSERT INTO user_interaction (live_id, user_id, comments, likes, gifts, score)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def init_and_seed(force: bool = False) -> None:
    rng = random.Random(20260309)
    now = datetime.now()
    base = now - timedelta(minutes=60)

    with get_connection() as conn:
        conn.executescript(SCHEMA_SQL)
        if force:
            conn.executescript(
                """
                DELETE FROM live_overview;
                DELETE FROM metric_trend;
                DELETE FROM interaction_heatmap;
                DELETE FROM ecommerce_funnel;
                DELETE FROM danmu;
                DELETE FROM user_interest;
                DELETE FROM user_interaction;
                """
            )
        count = conn.execute("SELECT COUNT(1) FROM live_overview").fetchone()[0]
        if count == 0:
            _seed_overview(conn, now)
            _seed_trend(conn, rng, base)
            _seed_heatmap(conn, rng)
            _seed_funnel(conn)
            _seed_danmu(conn, rng, base)
            _seed_user_interest(conn, rng)
            _seed_user_interaction(conn, rng)
        conn.commit()
