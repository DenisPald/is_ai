"""Сбор человеческого кода: репозитории без активности после 2021 года
(до выхода ChatGPT) на Python.

Запуск:  python -m src.collect.collect_human --max-files 300
"""
import argparse

from src.collect.common import (
    content_hash,
    is_relevant_path,
    is_valid_python,
    load_seen_hashes,
    save_file,
)
from src.collect.github_client import GitHubClient
from src.config import MAX_FILES_PER_REPO, RAW_AI_DIR, RAW_HUMAN_DIR

# Несколько запросов с разными звёздами — для разнообразия проектов.
# pushed:<2022-01-01 => репозиторий не трогали с до-ChatGPT эпохи.
QUERIES = [
    "language:Python pushed:<2022-01-01 stars:50..200",
    "language:Python pushed:<2022-01-01 stars:200..1000",
    "language:Python pushed:<2022-01-01 stars:1000..5000",
]


def collect(max_files: int) -> None:
    client = GitHubClient()
    seen = load_seen_hashes(RAW_HUMAN_DIR, RAW_AI_DIR)
    saved = 0

    for query in QUERIES:
        if saved >= max_files:
            break
        print(f"\n=== Запрос: {query} ===")
        for repo in client.search_repositories(query, max_repos=50):
            if saved >= max_files:
                break
            full_name = repo["full_name"]
            branch = repo.get("default_branch", "main")
            try:
                files = client.list_python_files(full_name, branch)
            except Exception as exc:  # noqa: BLE001 - сеть/доступ, просто пропускаем репо
                print(f"  ! {full_name}: {exc}")
                continue

            taken_here = 0
            for node in files:
                if saved >= max_files or taken_here >= MAX_FILES_PER_REPO:
                    break
                if not is_relevant_path(node["path"]):
                    continue
                source = client.get_blob_content(full_name, node["sha"])
                if not source or not is_valid_python(source):
                    continue
                h = content_hash(source)
                if h in seen:
                    continue
                seen.add(h)
                save_file(
                    source,
                    RAW_HUMAN_DIR,
                    label="human",
                    repo=full_name,
                    url=repo["html_url"],
                    source_signal=query,
                )
                saved += 1
                taken_here += 1
            if taken_here:
                print(f"  + {full_name}: {taken_here} файл(ов) (всего {saved})")

    print(f"\nГотово. Сохранено человеческих файлов: {saved}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-files", type=int, default=300)
    args = parser.parse_args()
    collect(args.max_files)
