from typing import Any

from app.agents.structurer import StructurerAgent
from app.pipeline.stages.base import PipelineStage, StageError


class StructureStage(PipelineStage):
    name = "structure"

    def __init__(self, llm_client=None):
        self.structurer = StructurerAgent(llm_client=llm_client)

    async def run(self, ctx: dict[str, Any]) -> dict[str, Any]:
        sections = ctx.get("sections", [])
        if not sections:
            return {"concepts": [], "structured_count": 0}

        concepts = []
        for section in sections:
            concept = await self.structurer.generate_concept(section, base_path="ingested")
            concepts.append(concept)

        return {"concepts": concepts, "structured_count": len(concepts)}
