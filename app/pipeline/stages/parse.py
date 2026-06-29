from typing import Any

from app.ingestion.router import IngestionRouter
from app.ingestion.cleaner import MarkdownCleaner
from app.pipeline.stages.base import PipelineStage, StageError


class ParseStage(PipelineStage):
    name = "parse"

    def __init__(self):
        self.router = IngestionRouter()
        self.cleaner = MarkdownCleaner()

    async def run(self, ctx: dict[str, Any]) -> dict[str, Any]:
        data: bytes = ctx.get("file_data")
        filename: str = ctx.get("filename", "")
        mime_hint: str = ctx.get("mime_hint", "")

        if not data:
            raise StageError("No file data provided", self.name, recoverable=False)

        try:
            parsed = self.router.route(data, filename=filename, mime_hint=mime_hint)
        except ValueError as e:
            raise StageError(str(e), self.name, recoverable=False)

        raw_md = parsed.raw_markdown
        cleaned = self.cleaner.clean(raw_md)

        return {
            "parsed_document": parsed,
            "raw_markdown": cleaned,
            "source_type": parsed.source_type,
        }
