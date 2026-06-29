from typing import Any

from app.agents.linker import LinkerAgent
from app.storage.bundle import BundleManager
from app.pipeline.stages.base import PipelineStage


class LinkStage(PipelineStage):
    name = "link"

    def __init__(self, bundle_manager: BundleManager, llm_client=None):
        self.linker = LinkerAgent(bundle_manager, llm_client=llm_client)

    async def run(self, ctx: dict[str, Any]) -> dict[str, Any]:
        concepts = ctx.get("concepts", [])
        if not concepts:
            return {"linked_concepts": [], "link_map": []}

        linked = []
        link_map = []
        for concept in concepts:
            linked_concept, linked_paths = await self.linker.link_concept(concept)
            linked.append(linked_concept)
            link_map.append((linked_concept.filepath, linked_paths))

        return {"linked_concepts": linked, "link_map": link_map, "linked_count": len(linked)}
