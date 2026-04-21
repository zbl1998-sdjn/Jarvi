from pathlib import Path

from app.services.search_service import SearchService


class KnowledgeContextService:
    def __init__(self, search_service: SearchService | None = None) -> None:
        self.search_service = search_service or SearchService()

    def build_context(self, query: str, limit: int = 3) -> str:
        results = self.search_service.search(query, "knowledge")[:limit]
        if not results:
            return ""

        return "\n\n".join(
            f"[{Path(result.path).name}] {result.snippet}"
            for result in results
        )
