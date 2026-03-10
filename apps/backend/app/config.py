from pathlib import Path


class Config:
    ROOT_DIR = Path(__file__).resolve().parents[3]
    DATA_DIR = ROOT_DIR / "data"
    DB_PATH = DATA_DIR / "system.db"
