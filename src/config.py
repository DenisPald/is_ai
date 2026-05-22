"""Пути проекта и конфигурация."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = ROOT / "data"
RAW_HUMAN_DIR = DATA_DIR / "raw" / "human"
RAW_AI_DIR = DATA_DIR / "raw" / "ai"
METADATA_CSV = DATA_DIR / "metadata.csv"
FEATURES_CSV = DATA_DIR / "features.csv"
REPORTS_DIR = ROOT / "reports"

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
GITHUB_API = "https://api.github.com"

# Фильтры качества для собираемых .py файлов.
MIN_LINES = 10
MAX_LINES = 500
# Максимум файлов из одного репозитория, чтобы один проект не доминировал.
MAX_FILES_PER_REPO = 5

for _d in (RAW_HUMAN_DIR, RAW_AI_DIR, REPORTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)
