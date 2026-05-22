"""Тонкая обёртка над GitHub REST API: поиск репозиториев, листинг файлов,
скачивание содержимого. Уважает rate-limit и делает retry."""
import base64
import time
from typing import Iterator

import requests

from src.config import GITHUB_API, GITHUB_TOKEN


class GitHubClient:
    def __init__(self, token: str = GITHUB_TOKEN):
        self.session = requests.Session()
        headers = {"Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self.session.headers.update(headers)

    def _get(self, url: str, params: dict | None = None) -> requests.Response:
        """GET с обработкой rate-limit и временных ошибок."""
        for attempt in range(5):
            resp = self.session.get(url, params=params, timeout=30)

            if resp.status_code == 403 and "rate limit" in resp.text.lower():
                reset = int(resp.headers.get("X-RateLimit-Reset", "0"))
                wait = max(reset - time.time(), 1) + 1
                print(f"[rate-limit] ждём {wait:.0f}с...")
                time.sleep(wait)
                continue

            if resp.status_code in (502, 503, 504):
                time.sleep(2 ** attempt)
                continue

            resp.raise_for_status()
            self._respect_search_limit(resp)
            return resp

        resp.raise_for_status()
        return resp

    @staticmethod
    def _respect_search_limit(resp: requests.Response) -> None:
        """Search API имеет отдельный лимит (~30 req/min). Притормаживаем у края."""
        if "/search/" not in resp.url:
            return
        remaining = int(resp.headers.get("X-RateLimit-Remaining", "99"))
        if remaining <= 1:
            reset = int(resp.headers.get("X-RateLimit-Reset", "0"))
            wait = max(reset - time.time(), 1) + 1
            print(f"[search-limit] ждём {wait:.0f}с...")
            time.sleep(wait)

    def search_repositories(
        self, query: str, max_repos: int = 50, sort: str = "stars"
    ) -> Iterator[dict]:
        """Итерирует репозитории по поисковому запросу (с пагинацией)."""
        per_page = 100
        fetched = 0
        page = 1
        while fetched < max_repos:
            params = {
                "q": query,
                "sort": sort,
                "order": "desc",
                "per_page": per_page,
                "page": page,
            }
            resp = self._get(f"{GITHUB_API}/search/repositories", params)
            items = resp.json().get("items", [])
            if not items:
                break
            for repo in items:
                yield repo
                fetched += 1
                if fetched >= max_repos:
                    return
            page += 1
            if page > 10:  # GitHub отдаёт максимум 1000 результатов поиска
                break

    def list_python_files(self, full_name: str, default_branch: str) -> list[dict]:
        """Возвращает blob-записи всех .py файлов репозитория (рекурсивно)."""
        url = f"{GITHUB_API}/repos/{full_name}/git/trees/{default_branch}"
        resp = self._get(url, params={"recursive": "1"})
        tree = resp.json().get("tree", [])
        return [
            node
            for node in tree
            if node.get("type") == "blob" and node.get("path", "").endswith(".py")
        ]

    def get_blob_content(self, full_name: str, sha: str) -> str | None:
        """Скачивает и декодирует содержимое blob по его sha."""
        url = f"{GITHUB_API}/repos/{full_name}/git/blobs/{sha}"
        resp = self._get(url)
        data = resp.json()
        if data.get("encoding") != "base64":
            return None
        try:
            return base64.b64decode(data["content"]).decode("utf-8")
        except (UnicodeDecodeError, ValueError):
            return None
