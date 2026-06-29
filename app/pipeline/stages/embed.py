import logging
from typing import Any, Optional

from app.config import settings
from app.pipeline.stages.base import PipelineStage

logger = logging.getLogger(__name__)


class EmbedStage(PipelineStage):
    name = "embed"

    def __init__(self, llm_client=None):
        self._llm = llm_client
        self._collection = None

    async def run(self, ctx: dict[str, Any]) -> dict[str, Any]:
        concepts = ctx.get("linked_concepts", ctx.get("concepts", []))
        workspace_id: str = ctx.get("workspace_id", "")
        use_chroma: bool = ctx.get("use_vector_store", bool(settings.gcp_project_id))

        if not concepts:
            return {"vectors_indexed": 0, "embedding_skipped": True}

        if not use_chroma and not self._llm:
            return {"vectors_indexed": 0, "embedding_skipped": True}

        indexed = 0
        vectors = []

        for concept in concepts:
            text = f"{concept.frontmatter.title or ''}\n{concept.body}"
            if not text.strip():
                continue

            vector = None
            if self._llm:
                try:
                    vector = self._llm.embed_text(text[:2000])
                except Exception:
                    logger.exception("Embedding failed for %s", concept.filepath)

            if use_chroma and vector:
                try:
                    await self._upsert_chroma(concept, vector, workspace_id)
                except Exception:
                    logger.warning("ChromaDB upsert failed for %s", concept.filepath)

            if vector:
                indexed += 1
                vectors.append({"filepath": concept.filepath, "vector": vector})

        return {
            "vectors_indexed": indexed,
            "embedding_skipped": indexed == 0 and bool(concepts),
            "total_concepts": len(concepts),
        }

    async def _upsert_chroma(self, concept, vector: list[float], workspace_id: str):
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        client = chromadb.Client(ChromaSettings(anonymized_telemetry=False))
        collection_name = f"workspace_{workspace_id}"
        self._collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        self._collection.upsert(
            ids=[concept.filepath],
            embeddings=[vector],
            metadatas=[{
                "filepath": concept.filepath,
                "title": concept.frontmatter.title or "",
                "type": concept.frontmatter.type,
                "tags": ",".join(concept.frontmatter.tags or []),
                "workspace_id": workspace_id,
            }],
            documents=[f"{concept.frontmatter.title or ''}\n{concept.body}"],
        )
