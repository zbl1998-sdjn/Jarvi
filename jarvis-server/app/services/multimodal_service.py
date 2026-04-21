from app.services.memory_service import MemoryService


class MultimodalService:
    def __init__(self) -> None:
        self.memory_service = MemoryService()

    def ingest_context(self, db, title: str, source_type: str, content: str) -> dict[str, object]:
        upload = self.memory_service.remember_upload(
            db,
            title=title,
            source_type=source_type,
            content=content,
        )
        return {
            "id": upload.id,
            "title": upload.title,
            "source_type": upload.source_type,
            "preview": upload.content[:120],
        }
