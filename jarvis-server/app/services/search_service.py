from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import quote_plus

import httpx

from app.config import ROOT_DIR, get_settings
from app.services.runtime_config_service import get_runtime_config


@dataclass(frozen=True)
class SearchResult:
    scope: str
    path: str
    title: str
    snippet: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


class SearchService:
    def _get_knowledge_root(self) -> Path:
        knowledge_root = get_runtime_config().knowledge_root
        return Path(knowledge_root) if knowledge_root else Path(get_settings().knowledge_root)

    def search(self, query: str, scope: str) -> list[SearchResult]:
        if scope == "web":
            return self.search_web(query)
        if scope == "auto":
            return self.search_auto(query)

        roots: dict[str, Path] = {
            "local": ROOT_DIR,
            "knowledge": self._get_knowledge_root(),
        }
        root = roots.get(scope, ROOT_DIR)
        if not root.exists():
            return []

        results: list[SearchResult] = []
        lowered_query = query.lower()
        for path in root.rglob("*.md"):
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if lowered_query not in text.lower() and lowered_query not in path.name.lower():
                continue
            first_match = next(
                (line.strip() for line in text.splitlines() if lowered_query in line.lower()),
                path.name,
            )
            results.append(
                SearchResult(
                    scope=scope,
                    path=str(path),
                    title=path.name,
                    snippet=first_match[:180],
                )
            )
            if len(results) == 5:
                break
        return results

    def search_auto(self, query: str) -> list[SearchResult]:
        combined = [*self.search(query, "knowledge"), *self.search(query, "local")]
        if combined:
            return combined[:6]
        return self.search_web(query)

    def search_web(self, query: str) -> list[SearchResult]:
        response = httpx.get(
            "https://api.duckduckgo.com/",
            params={
                "q": query,
                "format": "json",
                "no_redirect": "1",
                "no_html": "1",
            },
            timeout=10.0,
        )
        response.raise_for_status()
        payload = response.json()
        results: list[SearchResult] = []

        abstract = str(payload.get("AbstractText", "")).strip()
        if abstract:
            results.append(
                SearchResult(
                    scope="web",
                    path=str(payload.get("AbstractURL") or f"https://duckduckgo.com/?q={quote_plus(query)}"),
                    title=str(payload.get("Heading") or query),
                    snippet=abstract[:180],
                )
            )

        related_topics = payload.get("RelatedTopics", [])
        for item in related_topics:
            if not isinstance(item, dict):
                continue
            if "Topics" in item:
                nested_items = item.get("Topics", [])
            else:
                nested_items = [item]
            for nested in nested_items:
                if not isinstance(nested, dict):
                    continue
                text = str(nested.get("Text", "")).strip()
                url = str(nested.get("FirstURL", "")).strip()
                if not text or not url:
                    continue
                title = text.split(" - ", 1)[0]
                results.append(
                    SearchResult(
                        scope="web",
                        path=url,
                        title=title[:100],
                        snippet=text[:180],
                    )
                )
                if len(results) >= 5:
                    return results
        return results
