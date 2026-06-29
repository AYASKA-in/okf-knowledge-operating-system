import pytest
import os
import tempfile
import shutil

from datetime import datetime

from app.agents.ingestor import IngestorAgent
from app.agents.structurer import StructurerAgent
from app.models.okf import OKFConcept, OKFFrontmatter


@pytest.mark.asyncio
class TestIngestorAgent:
    async def test_process_simple_text(self):
        agent = IngestorAgent()
        text = "Simple content without headings."
        results = await agent.process(text, filename="test.txt")
        assert len(results) == 1
        assert results[0]["section_title"] == "test"
        assert results[0]["raw_text"] == "Simple content without headings."

    async def test_process_with_headings(self):
        agent = IngestorAgent()
        text = "# Heading One\n\nContent one.\n\n## Heading Two\n\nContent two."
        results = await agent.process(text, filename="doc.txt")
        assert len(results) >= 2
        titles = [r["section_title"] for r in results]
        assert "Heading One" in titles or "Heading Two" in titles


@pytest.mark.asyncio
class TestStructurerAgent:
    async def test_generate_concept(self):
        agent = StructurerAgent()
        section = {
            "section_title": "Remote Work Policy",
            "raw_text": "Employees must comply with the remote work policy. All remote workers are required to follow security guidelines.",
            "hash": "abc123",
        }
        concept = await agent.generate_concept(section, base_path="hr")
        assert concept.filepath == "hr/remote-work-policy.md"
        assert concept.frontmatter.type == "policy"
        assert concept.frontmatter.title == "Remote Work Policy"
        assert concept.frontmatter.tags is not None
        assert len(concept.frontmatter.tags) > 0

    async def test_concept_to_markdown_roundtrip(self):
        agent = StructurerAgent()
        section = {
            "section_title": "Test Concept",
            "raw_text": "Test body content.",
            "hash": "def456",
        }
        concept = await agent.generate_concept(section, base_path="")
        md = concept.to_markdown()

        parsed = OKFConcept.from_markdown(concept.filepath, md)
        assert parsed.frontmatter.type == concept.frontmatter.type
        assert parsed.frontmatter.title == concept.frontmatter.title
        assert parsed.body == concept.body

    async def test_uses_md_links_not_wiki_links(self):
        concept = OKFConcept(
            filepath="test.md",
            frontmatter=OKFFrontmatter(type="reference", title="Test Links"),
            body="See [Policy](./policy.md) for details."
        )
        md = concept.to_markdown()
        assert "[[" not in md
        assert "[Policy](./policy.md)" in md


class TestOKFConceptModel:
    def test_extract_md_links(self):
        concept = OKFConcept(
            filepath="test.md",
            frontmatter=OKFFrontmatter(type="test", title="Link Test"),
            body="# Links\n\nSee [Policy](../hr/policy.md) and [External](https://example.com)."
        )
        links = concept.extract_links()
        assert "../hr/policy.md" in links
        assert "https://example.com" in links

    def test_rejects_wiki_links_in_extract(self):
        concept = OKFConcept(
            filepath="test.md",
            frontmatter=OKFFrontmatter(type="test"),
            body="[[Bad Link]] should not be present."
        )
        links = concept.extract_links()
        for link in links:
            assert "[[" not in link


class TestOKFConceptAdditional:
    def test_timestamp_coerced_from_datetime(self):
        from datetime import timezone
        fm = OKFFrontmatter(
            type="doc",
            timestamp=datetime(2026, 6, 29, 9, 25, 38, tzinfo=timezone.utc),
        )
        assert isinstance(fm.timestamp, str)
        assert "2026-06-29" in fm.timestamp
