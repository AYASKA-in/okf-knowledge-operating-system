import hashlib
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.config import settings


SECTION_PROMPT = """You are an expert document analyst. Given the raw text below, identify the distinct logical sections.
Return a JSON array of objects, each with "title" and "text" keys.
Each section should be a self-contained topic.
Include the section heading as part of the text.

Raw text:
{text}

Return ONLY a valid JSON array, no other text.
"""


class IngestorAgent:
    def __init__(self, llm_client=None, model_name: Optional[str] = None):
        self._llm = llm_client
        self.model_name = model_name or settings.ingestion_model

    async def process(self, content: str, filename: Optional[str] = None,
                      source_type: Optional[str] = None) -> List[Dict[str, Any]]:
        sections = await self._split_sections(content, filename or "unknown")

        results = []
        for section in sections:
            section_text = section["text"]
            section_hash = hashlib.sha256(section_text.encode("utf-8")).hexdigest()[:12]
            results.append({
                "hash": section_hash,
                "source": filename or "direct_input",
                "source_type": source_type or "text",
                "section_title": section["title"],
                "raw_text": section["text"],
                "tokens_estimate": len(section["text"]) // 4,
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            })
        return results

    async def _split_sections(self, content: str, filename: str) -> List[Dict[str, str]]:
        if self._llm:
            try:
                sections = await self._split_with_llm(content)
                if sections:
                    return sections
            except Exception:
                pass
        return self._split_into_sections(content.split("\n"), filename)

    async def _split_with_llm(self, content: str) -> Optional[List[Dict[str, str]]]:
        prompt = SECTION_PROMPT.format(text=content[:8000])
        result = await self._llm.generate_text_async(prompt)
        if not result:
            return None
        try:
            sections = json.loads(result)
            if isinstance(sections, list) and all("title" in s and "text" in s for s in sections):
                return sections
        except (json.JSONDecodeError, ValueError):
            pass
        return None

    def _split_into_sections(self, lines: List[str], filename: str) -> List[Dict[str, str]]:
        sections = []
        current_title = Path(filename).stem if "." in filename else filename
        current_lines = []

        heading_pattern = re.compile(r'^(#{1,3})\s+(.+)$')

        for line in lines:
            match = heading_pattern.match(line)
            if match:
                if current_lines:
                    sections.append({
                        "title": current_title,
                        "text": "\n".join(current_lines).strip()
                    })
                current_title = match.group(2).strip()
                current_lines = [line]
            else:
                current_lines.append(line)

        if current_lines:
            sections.append({
                "title": current_title,
                "text": "\n".join(current_lines).strip()
            })

        return [s for s in sections if s["text"]]
