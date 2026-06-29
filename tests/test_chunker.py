"""Unit tests for ChunkerAgent."""
import pytest
from app.ingestion.chunker import ChunkerAgent


def _make_section(text: str, title: str = "Test", idx: int = 0) -> dict:
    import hashlib
    return {
        "hash": hashlib.sha256(text.encode("utf-8")).hexdigest()[:12],
        "section_title": title,
        "raw_text": text,
        "source": "test.md",
        "source_type": "text",
        "tokens_estimate": len(text) // 4,
    }


class TestChunkerAgent:
    def test_passthrough_below_threshold(self):
        text = "A" * 500
        section = _make_section(text)
        chunker = ChunkerAgent(max_chars=10000)
        result = chunker.chunk([section])
        assert len(result) == 1
        assert result[0]["raw_text"] == text
        assert "chunk_index" not in result[0]
        assert "parent_hash" not in result[0]

    def test_splits_above_threshold(self):
        text = "A" * 25000
        section = _make_section(text)
        chunker = ChunkerAgent(max_chars=10000, overlap_chars=500)
        result = chunker.chunk([section])
        assert len(result) >= 2
        for chunk in result:
            assert len(chunk["raw_text"]) <= 10000
            assert "chunk_index" in chunk
            assert chunk["parent_hash"] == section["hash"]
            assert chunk["section_title"].startswith("Test (part ")

    def test_chunks_cover_full_text(self):
        text = "B" * 25000
        section = _make_section(text)
        chunker = ChunkerAgent(max_chars=10000, overlap_chars=500)
        result = chunker.chunk([section])
        combined = "".join(c["raw_text"] for c in result)
        assert len(combined) >= len(text)

    def test_chunk_indices_are_sequential(self):
        text = "C" * 25000
        section = _make_section(text)
        chunker = ChunkerAgent(max_chars=10000, overlap_chars=500)
        result = chunker.chunk([section])
        indices = [c["chunk_index"] for c in result]
        assert indices == list(range(len(result)))

    def test_overlap_preserves_context(self):
        text = "X" * 8000 + "SENTINEL_MARKER" + "Y" * 8000
        section = _make_section(text)
        chunker = ChunkerAgent(max_chars=10000, overlap_chars=2000)
        result = chunker.chunk([section])
        # The overlap should cause the boundary to be somewhere in the middle
        # so "SENTINEL_MARKER" should appear in at least one chunk
        assert any("SENTINEL_MARKER" in c["raw_text"] for c in result)

    def test_multiple_sections(self):
        s1 = _make_section("A" * 500, title="First")
        s2 = _make_section("B" * 30000, title="Second")
        chunker = ChunkerAgent(max_chars=10000, overlap_chars=500)
        result = chunker.chunk([s1, s2])
        # s1 should passthrough, s2 should split
        assert len(result) >= 2
        assert result[0]["section_title"] == "First"
        assert result[1]["section_title"].startswith("Second (part 1)")
        assert result[0].get("chunk_index") is None  # passthrough

    def test_overlap_smaller_than_chunk(self):
        text = "D" * 30000
        section = _make_section(text)
        chunker = ChunkerAgent(max_chars=15000, overlap_chars=5000)
        result = chunker.chunk([section])
        assert len(result) == 3
        # chunk 0: 0-15000, chunk 1: 10000-25000, chunk 2: 20000-30000
        assert 0 <= len(result[2]["raw_text"]) <= 15000

    def test_overlap_greater_than_max_chars_clamps(self):
        text = "E" * 10000
        section = _make_section(text)
        chunker = ChunkerAgent(max_chars=5000, overlap_chars=8000)
        result = chunker.chunk([section])
        assert len(result) >= 1
        for chunk in result:
            assert len(chunk["raw_text"]) <= 5000

    def test_exact_threshold_no_split(self):
        text = "F" * 10000
        section = _make_section(text)
        chunker = ChunkerAgent(max_chars=10000)
        result = chunker.chunk([section])
        assert len(result) == 1

    def test_one_char_over_threshold_splits(self):
        text = "G" * 10001
        section = _make_section(text)
        chunker = ChunkerAgent(max_chars=10000)
        result = chunker.chunk([section])
        assert len(result) == 2

    def test_empty_section(self):
        section = _make_section("", title="Empty")
        chunker = ChunkerAgent()
        result = chunker.chunk([section])
        assert len(result) == 1
        assert result[0]["raw_text"] == ""

    def test_tokens_estimate_integrity(self):
        text = "H" * 12000
        section = _make_section(text)
        chunker = ChunkerAgent(max_chars=5000, overlap_chars=500)
        result = chunker.chunk([section])
        for chunk in result:
            expected_tokens = len(chunk["raw_text"]) // 4
            assert chunk["tokens_estimate"] == expected_tokens

    def test_empty_sections_list(self):
        chunker = ChunkerAgent()
        result = chunker.chunk([])
        assert result == []
