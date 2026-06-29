from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from app.storage.bundle import BundleManager
from app.config import settings


CHAT_SYSTEM_PROMPT = """You are a precise enterprise knowledge assistant.
You answer questions using ONLY the provided OKF (Open Knowledge Format) markdown files.

Rules:
- Answer ONLY from the provided context files. Do NOT use external knowledge.
- If the answer is not contained in the provided files, say "I cannot answer this from the available knowledge base."
- Cite the specific file paths for every claim you make.
- Use bullet points for clarity when listing multiple items.
- Be concise and factual. Do not add speculation.

Retrieved Context:
{context}

User Question: {question}
"""


class ChatAgent:
    def __init__(self, bundle_manager: BundleManager, llm_client=None,
                 model_name: Optional[str] = None):
        self.bundle = bundle_manager
        self._llm = llm_client
        self.model_name = model_name or settings.chat_model

    async def answer(self, question: str,
                     conversation_id: Optional[str] = None) -> Dict[str, Any]:
        context, citations = await self._retrieve_context(question)

        if not context:
            return {
                "answer": "I cannot answer this from the available knowledge base. No relevant concepts were found.",
                "citations": [],
                "conversation_id": conversation_id or datetime.now(timezone.utc).isoformat(),
            }

        rendered_prompt = CHAT_SYSTEM_PROMPT.format(context=context, question=question)

        if self._llm:
            try:
                answer = await self._llm.generate_text_async(
                    rendered_prompt,
                    model_name=self.model_name,
                    temperature=0.1,
                    max_tokens=2048,
                )
                if answer:
                    return {
                        "answer": answer,
                        "citations": citations,
                        "conversation_id": conversation_id or datetime.now(timezone.utc).isoformat(),
                    }
            except Exception:
                pass

        return {
            "answer": rendered_prompt,
            "citations": citations,
            "conversation_id": conversation_id or datetime.now(timezone.utc).isoformat(),
        }

    async def _retrieve_context(self, question: str) -> tuple[str, List[Dict[str, Any]]]:
        q_lower = question.lower()
        query_words = set(q_lower.split())

        all_concepts = self.bundle.list_concepts()
        scored: List[tuple[int, Any]] = []

        for concept in all_concepts:
            score = self._score_concept(concept, query_words, q_lower)
            if score > 0:
                scored.append((score, concept))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:5]

        if not top:
            return "", []

        context_parts = []
        citations = []

        for score, concept in top:
            header = f"### Source: {concept.filepath}"
            if concept.frontmatter.title:
                header += f" — {concept.frontmatter.title}"
            context_parts.append(f"{header}\n\n{concept.body}")
            citations.append({
                "filepath": concept.filepath,
                "title": concept.frontmatter.title or "",
                "type": concept.frontmatter.type,
                "relevance_score": score,
            })

        return "\n\n---\n\n".join(context_parts), citations

    def _score_concept(self, concept, query_words: set, q_lower: str) -> int:
        score = 0
        title = (concept.frontmatter.title or "").lower()
        body = concept.body.lower()
        tags = [t.lower() for t in (concept.frontmatter.tags or [])]

        if q_lower in title:
            score += 10

        title_words = set(title.split())
        word_overlap = query_words & title_words
        score += len(word_overlap) * 5

        tag_overlap = query_words & set(tags)
        score += len(tag_overlap) * 3

        if q_lower in body:
            score += 2

        for word in query_words:
            if len(word) > 3 and word in body:
                score += 1

        return score
