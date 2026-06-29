from typing import Any

from app.ingestion.chunker import ChunkerAgent
from app.agents.ingestor import IngestorAgent
from app.pipeline.stages.base import PipelineStage, StageError


class ChunkStage(PipelineStage):
    name = "chunk"

    def __init__(self, llm_client=None):
        self.ingestor = IngestorAgent(llm_client=llm_client)
        self.chunker = ChunkerAgent()

    async def run(self, ctx: dict[str, Any]) -> dict[str, Any]:
        raw_md: str = ctx.get("raw_markdown", "")
        filename: str = ctx.get("filename", "")
        source_type: str = ctx.get("source_type", "text")

        if not raw_md:
            raise StageError("No markdown content to chunk", self.name, recoverable=False)

        sections = await self.ingestor.process(
            content=raw_md,
            filename=filename,
            source_type=source_type,
        )

        chunked = self.chunker.chunk(sections)

        return {"sections": chunked}
