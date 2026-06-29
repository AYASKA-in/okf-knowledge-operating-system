import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.models.okf import OKFConcept, OKFFrontmatter


STRUCTURING_PROMPT = """You are an OKF (Open Knowledge Format) Structuring Agent.
Convert the following raw document section into a structured OKF Markdown concept file.

Rules:
1. YAML frontmatter MUST contain at minimum a 'type' field.
2. Use standard Markdown links [text](./path.md) — NEVER use wiki-style [[brackets]].
3. The body must be clean, factual, and retain the original meaning.
4. Infer the 'type' from content (policy, guideline, reference, procedure, glossary, etc).
5. Include relevant 'tags' in the frontmatter.

Raw section title: {title}
Raw text:
{text}

Return ONLY the OKF Markdown output with YAML frontmatter delimited by ---.
"""


class StructurerAgent:
    def __init__(self, llm_client=None):
        self._llm = llm_client

    async def generate_concept(self, section: Dict[str, Any],
                                base_path: str) -> OKFConcept:
        title = section.get("section_title", "Untitled")
        slug = self._slugify(title)
        filepath = f"{base_path}/{slug}.md" if base_path else f"{slug}.md"

        if self._llm:
            try:
                concept = await self._generate_with_llm(section, filepath)
                if concept is not None:
                    return concept
            except Exception:
                pass

        frontmatter = self._infer_frontmatter(section, title)
        body = self._generate_body(section)

        return OKFConcept(
            filepath=filepath,
            frontmatter=frontmatter,
            body=body,
        )

    async def _generate_with_llm(self, section: Dict[str, Any], filepath: str) -> Optional[OKFConcept]:
        title = section.get("section_title", "Untitled")
        raw_text = section.get("raw_text", "")
        prompt = STRUCTURING_PROMPT.format(title=title, text=raw_text)

        result = await self._llm.generate_text_async(prompt)
        if not result or "---" not in result:
            return None

        try:
            return OKFConcept.from_markdown(filepath, result)
        except Exception:
            return None

    def _slugify(self, text: str) -> str:
        slug = text.lower().strip()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s_]+', '-', slug)
        slug = re.sub(r'-+', '-', slug)
        return slug[:80].rstrip("-")

    def _infer_frontmatter(self, section: Dict, title: str) -> OKFFrontmatter:
        raw = section.get("raw_text", "")
        tags = []

        type_map = {
            "policy": ["policy", "compliance", "regulation", "must", "shall", "required"],
            "procedure": ["procedure", "how to", "steps", "workflow", "process"],
            "guideline": ["guideline", "recommend", "best practice", "suggest"],
            "reference": ["reference", "glossary", "definition", "overview"],
            "faq": ["faq", "frequently asked", "common question"],
        }

        raw_lower = raw.lower()[:500]
        for ctype, keywords in type_map.items():
            if any(kw in raw_lower for kw in keywords):
                tags.append(ctype)

        if not tags:
            tags.append("general")

        return OKFFrontmatter(
            type=tags[0],
            title=title,
            description=raw[:200].strip() if len(raw) > 20 else title,
            tags=tags,
            timestamp=datetime.now(timezone.utc).isoformat(),
            status="draft",
        )

    def _generate_body(self, section: Dict) -> str:
        title = section.get("section_title", "Untitled")
        raw_text = section.get("raw_text", "")
        return f"# {title}\n\n{raw_text}"
