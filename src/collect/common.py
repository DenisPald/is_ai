"""Общая логика сбора: фильтрация файлов, дедупликация, сохранение, метаданные."""
import ast
import csv
import hashlib
import re
from pathlib import Path

from src.config import MAX_LINES, METADATA_CSV, MIN_LINES

# Имена/пути, которые отсеиваем как малоинформативные или авто-генерённые.
_SKIP_PATTERNS = re.compile(
    r"(^|/)(__init__\.py$|setup\.py$|conftest\.py$|.*_pb2\.py$"
    r"|migrations/|tests?/|test_|.*_test\.py$)",
    re.IGNORECASE,
)

_METADATA_HEADER = ["file", "label", "repo", "url", "source_signal"]


def is_relevant_path(path: str) -> bool:
    return _SKIP_PATTERNS.search(path) is None


def is_valid_python(source: str) -> bool:
    """Файл должен парситься и попадать в разумный диапазон по числу строк."""
    n_lines = source.count("\n") + 1
    if not (MIN_LINES <= n_lines <= MAX_LINES):
        return False
    try:
        ast.parse(source)
    except (SyntaxError, ValueError):
        return False
    return True


def content_hash(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def load_seen_hashes(*dirs: Path) -> set[str]:
    """Хеши уже сохранённых файлов — для дедупликации между запусками."""
    seen = set()
    for d in dirs:
        for f in d.glob("*.py"):
            seen.add(content_hash(f.read_text(encoding="utf-8", errors="ignore")))
    return seen


def _append_metadata(row: dict) -> None:
    new_file = not METADATA_CSV.exists()
    with METADATA_CSV.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_METADATA_HEADER)
        if new_file:
            writer.writeheader()
        writer.writerow(row)


def save_file(
    source: str, out_dir: Path, label: str, repo: str, url: str, source_signal: str
) -> str:
    """Сохраняет файл под именем-хешем и дописывает строку в metadata.csv."""
    h = content_hash(source)
    fname = f"{label}_{h[:16]}.py"
    (out_dir / fname).write_text(source, encoding="utf-8")
    _append_metadata(
        {
            "file": fname,
            "label": label,
            "repo": repo,
            "url": url,
            "source_signal": source_signal,
        }
    )
    return fname
