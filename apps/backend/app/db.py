import sqlite3
from pathlib import Path

from .config import Config


def _ensure_data_dir() -> None:
    Path(Config.DATA_DIR).mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    _ensure_data_dir()
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
