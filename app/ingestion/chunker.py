import hashlib
import math
from typing import List, Dict, Any


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _estimate_tokens(text: str) -> int:
    return len(text) // 4


class ChunkerAgent:
    def __init__(self, max_chars: int = 10000, overlap_chars: int = 500):
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars

    def chunk(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        for section in sections:
            text = section.get("raw_text", "")
            if len(text) <= self.max_chars:
                result.append(section)
                continue

            parent_hash = section.get("hash", _hash_text(text))
            title = section.get("section_title", "Untitled")
            step = self.max_chars - self.overlap_chars
            if step < 1:
                step = self.max_chars

            chunks = []
            start = 0
            while start < len(text):
                end = min(start + self.max_chars, len(text))
                chunk_text = text[start:end]
                chunk_index = len(chunks)
                chunk = dict(section)
                chunk["raw_text"] = chunk_text
                chunk["hash"] = _hash_text(chunk_text)
                chunk["parent_hash"] = parent_hash
                chunk["chunk_index"] = chunk_index
                chunk["tokens_estimate"] = _estimate_tokens(chunk_text)
                chunk["section_title"] = f"{title} (part {chunk_index + 1})"
                chunks.append(chunk)
                if end >= len(text):
                    break
                start += step

            result.extend(chunks)

        return result
