import math
from typing import List, Dict, Optional, Set, Tuple
from app.models.okf import OKFConcept
from app.storage.bundle import BundleManager


class LinkerAgent:
    def __init__(self, bundle_manager: BundleManager, llm_client=None):
        self.bundle = bundle_manager
        self._llm = llm_client
        self._embedding_cache: Dict[str, List[float]] = {}

    async def link_concept(self, concept: OKFConcept) -> Tuple[OKFConcept, List[str]]:
        existing_concepts = self.bundle.list_concepts()
        if not existing_concepts:
            return concept, []

        concept_title = (concept.frontmatter.title or "").lower()
        concept_body = concept.body.lower()
        concept_tags = set(concept.frontmatter.tags or [])

        new_embedding = None
        if self._llm:
            embed_text = f"{concept_title}\n{concept_body[:1000]}"
            new_embedding = self._llm.embed_text(embed_text)

        linked: Dict[str, str] = {}

        for existing in existing_concepts:
            if existing.filepath == concept.filepath:
                continue
            score = self._compute_relevance(
                concept_title, concept_body, concept_tags, existing,
                new_embedding,
            )
            if score >= 2:
                rel_path = self._relative_link(concept.filepath, existing.filepath)
                linked[existing.filepath] = rel_path

        if linked and "## See Also" not in concept.body:
            see_also_section = "\n## See Also\n\n"
            for abs_path in sorted(linked):
                target_title = self._extract_title(linked[abs_path])
                see_also_section += f"- [{target_title}]({linked[abs_path]})\n"
            concept.body = concept.body.rstrip() + see_also_section

        return concept, list(linked.keys())

    def _compute_relevance(self, new_title: str, new_body: str,
                            new_tags: Set[str], existing: OKFConcept,
                            new_embedding: Optional[List[float]] = None) -> float:
        score = 0.0
        ex_title = (existing.frontmatter.title or "").lower()
        ex_body = existing.body.lower()
        ex_tags = set(existing.frontmatter.tags or [])

        common_tags = new_tags & ex_tags
        score += len(common_tags)

        title_words = set(new_title.split()) & set(ex_title.split())
        score += len(title_words) * 2

        for word in new_title.split():
            if len(word) > 3 and word in ex_body:
                score += 1

        if new_embedding and self._llm:
            ex_embedding = self._get_or_compute_embedding(existing, ex_title, ex_body)
            if ex_embedding:
                sim = self._cosine_similarity(new_embedding, ex_embedding)
                score += sim * 5

        return score

    def _get_or_compute_embedding(self, concept: OKFConcept, title: str, body: str) -> Optional[List[float]]:
        if concept.filepath in self._embedding_cache:
            return self._embedding_cache[concept.filepath]
        embed_text = f"{title}\n{body[:1000]}"
        embedding = self._llm.embed_text(embed_text)
        if embedding:
            self._embedding_cache[concept.filepath] = embedding
        return embedding

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        if not a or not b:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _relative_link(self, from_path: str, to_path: str) -> str:
        import os
        from_dir = os.path.dirname(from_path) if "/" in from_path else "."
        rel = os.path.relpath(to_path, from_dir).replace("\\", "/")
        return rel

    def _extract_title(self, filepath: str) -> str:
        import os
        base = os.path.basename(filepath)
        return os.path.splitext(base)[0].replace("-", " ").title()
