from typing import Any
from datetime import datetime, timezone

from app.storage.bundle import BundleManager
from app.pipeline.stages.base import PipelineStage


class IndexStage(PipelineStage):
    name = "index"

    def __init__(self, bundle_manager: BundleManager):
        self.bundle = bundle_manager

    async def run(self, ctx: dict[str, Any]) -> dict[str, Any]:
        concepts = ctx.get("linked_concepts", ctx.get("concepts", []))
        filename: str = ctx.get("filename", "unknown")

        index = self._update_index(concepts)
        self._update_log(concepts, filename)

        return {
            "index_updated": index,
            "concepts_written": len(concepts),
        }

    def _update_index(self, concepts) -> bool:
        all_concepts = self.bundle.list_concepts()
        existing_paths = {c.filepath for c in all_concepts}
        new_paths = {c.filepath for c in concepts}

        if not new_paths - existing_paths:
            return False

        index_md = f"---\ntype: directory\ntitle: Workspace Index\ndescription: Auto-generated index\n---\n\n# Concepts\n\n"
        for c in all_concepts:
            title = c.frontmatter.title or c.filepath
            index_md += f"- [{title}]({c.filepath})\n"

        self.bundle.write_concept(self._make_index_concept(index_md))
        return True

    def _update_log(self, concepts, filename: str):
        for c in concepts:
            self.bundle._append_to_log("ingest", f"{c.filepath} (via {filename})")

    def _make_index_concept(self, md: str):
        from app.models.okf import OKFConcept, OKFFrontmatter
        return OKFConcept(
            filepath="index.md",
            frontmatter=OKFFrontmatter(
                type="directory",
                title="Workspace Index",
                timestamp=datetime.now(timezone.utc).isoformat(),
            ),
            body=md,
        )
