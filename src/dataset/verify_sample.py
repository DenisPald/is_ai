"""Ручная проверка чистоты ИИ-меток.

Метки ИИ-класса шумные ("репо помечен как AI" != "весь код сгенерирован"),
поэтому отбираем случайную выборку и просматриваем глазами.

Просмотреть выборку:
    python -m src.dataset.verify_sample --sample 20

Отбраковать файлы, оказавшиеся не-ИИ (удалит их и почистит metadata.csv):
    python -m src.dataset.verify_sample --reject ai_abc123.py ai_def456.py
"""
import argparse
import csv
import random

from src.config import METADATA_CSV, RAW_AI_DIR


def show_sample(n: int) -> None:
    files = sorted(RAW_AI_DIR.glob("*.py"))
    if not files:
        print("Нет ИИ-файлов. Сначала запустите src.collect.collect_ai")
        return
    repo_by_file = _repo_map()
    for f in random.sample(files, min(n, len(files))):
        print("=" * 70)
        print(f"ФАЙЛ: {f.name}   РЕПО: {repo_by_file.get(f.name, '?')}")
        print("-" * 70)
        print(f.read_text(encoding="utf-8", errors="ignore"))
    print("=" * 70)
    print(
        f"Показано {min(n, len(files))} из {len(files)}. "
        "Файлы, которые НЕ похожи на ИИ-код, передайте в --reject."
    )


def reject(filenames: list[str]) -> None:
    removed = 0
    for name in filenames:
        path = RAW_AI_DIR / name
        if path.exists():
            path.unlink()
            removed += 1
        else:
            print(f"  ! не найден: {name}")
    _drop_from_metadata(set(filenames))
    print(f"Удалено файлов: {removed}. metadata.csv обновлён.")


def _repo_map() -> dict[str, str]:
    if not METADATA_CSV.exists():
        return {}
    with METADATA_CSV.open(encoding="utf-8") as fh:
        return {row["file"]: row["repo"] for row in csv.DictReader(fh)}


def _drop_from_metadata(to_drop: set[str]) -> None:
    if not METADATA_CSV.exists():
        return
    with METADATA_CSV.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = [r for r in reader if r["file"] not in to_drop]
        header = reader.fieldnames
    with METADATA_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=20)
    parser.add_argument("--reject", nargs="*", default=None)
    args = parser.parse_args()
    if args.reject is not None:
        reject(args.reject)
    else:
        show_sample(args.sample)
