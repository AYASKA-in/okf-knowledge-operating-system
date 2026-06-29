"""Tests for LLM client and agent LLM integration."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.llm.client import VertexAIClient


@pytest.fixture(autouse=True)
def reset_settings():
    """Ensure gcp_project_id is empty for fallback tests."""
    import app.config
    app.config.settings.gcp_project_id = ""
    yield


class TestVertexAIClient:
    def test_fallback_generate_text_returns_empty(self):
        client = VertexAIClient()
        result = client.generate_text("test prompt")
        assert result == ""

    @pytest.mark.asyncio
    async def test_fallback_generate_text_async_returns_empty(self):
        client = VertexAIClient()
        result = await client.generate_text_async("test prompt")
        assert result == ""

    def test_fallback_embed_text_returns_empty_list(self):
        client = VertexAIClient()
        result = client.embed_text("test text")
        assert result == []

    def test_cosine_similarity_identical(self):
        from app.agents.linker import LinkerAgent
        agent = LinkerAgent.__new__(LinkerAgent)
        a = [0.1, 0.2, 0.3]
        sim = agent._cosine_similarity(a, a)
        assert abs(sim - 1.0) < 1e-6

    def test_cosine_similarity_orthogonal(self):
        from app.agents.linker import LinkerAgent
        agent = LinkerAgent.__new__(LinkerAgent)
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        sim = agent._cosine_similarity(a, b)
        assert abs(sim) < 1e-6

    def test_cosine_similarity_empty(self):
        from app.agents.linker import LinkerAgent
        agent = LinkerAgent.__new__(LinkerAgent)
        assert agent._cosine_similarity([], [1.0]) == 0.0
        assert agent._cosine_similarity([1.0], []) == 0.0
        assert agent._cosine_similarity([], []) == 0.0


class MockLLMClient:
    """Mock LLM client for testing agent LLM integration."""

    def __init__(self):
        self.generate_text_async = AsyncMock(return_value="Mocked response")
        self.embed_text = MagicMock(return_value=[0.1, 0.2, 0.3])


class TestIngestorAgentWithLLM:
    @pytest.mark.asyncio
    async def test_fallback_to_rule_based_when_llm_returns_empty(self):
        from app.agents.ingestor import IngestorAgent
        mock_llm = MockLLMClient()
        mock_llm.generate_text_async = AsyncMock(return_value="")
        agent = IngestorAgent(llm_client=mock_llm)
        sections = await agent.process("Some content\n\nMore lines", "test.txt")
        assert len(sections) == 1
        assert sections[0]["section_title"] == "test"

    @pytest.mark.asyncio
    async def test_fallback_to_rule_based_when_llm_returns_bad_json(self):
        from app.agents.ingestor import IngestorAgent
        mock_llm = MockLLMClient()
        mock_llm.generate_text_async = AsyncMock(return_value="not json at all")
        agent = IngestorAgent(llm_client=mock_llm)
        sections = await agent.process("# Title\n\nContent", "test.txt")
        assert sections[0]["section_title"] == "Title"

    @pytest.mark.asyncio
    async def test_no_llm_fallback(self):
        from app.agents.ingestor import IngestorAgent
        agent = IngestorAgent()
        sections = await agent.process("# Title\n\nContent", "test.txt")
        assert len(sections) == 1
        assert sections[0]["section_title"] == "Title"


class TestStructurerAgentWithLLM:
    @pytest.mark.asyncio
    async def test_fallback_when_llm_returns_no_frontmatter(self):
        from app.agents.structurer import StructurerAgent
        mock_llm = MockLLMClient()
        mock_llm.generate_text_async = AsyncMock(return_value="no frontmatter here")
        agent = StructurerAgent(llm_client=mock_llm)
        concept = await agent.generate_concept(
            {"section_title": "Test", "raw_text": "Some content"},
            "base",
        )
        assert concept.filepath == "base/test.md"
        assert concept.frontmatter.type is not None

    @pytest.mark.asyncio
    async def test_parses_llm_output_with_frontmatter(self):
        from app.agents.structurer import StructurerAgent
        mock_llm = MockLLMClient()
        okf_output = """---
type: guideline
title: Test Concept
tags:
  - guideline
  - reference
---

# Test Concept

Some content here."""
        mock_llm.generate_text_async = AsyncMock(return_value=okf_output)
        agent = StructurerAgent(llm_client=mock_llm)
        concept = await agent.generate_concept(
            {"section_title": "Test", "raw_text": "Some content"},
            "ingested",
        )
        assert concept.filepath == "ingested/test.md"
        assert concept.frontmatter.type == "guideline"
        assert "Test Concept" in concept.body

    @pytest.mark.asyncio
    async def test_no_llm_fallback(self):
        from app.agents.structurer import StructurerAgent
        agent = StructurerAgent()
        concept = await agent.generate_concept(
            {"section_title": "Policy", "raw_text": "All employees must comply."},
            "ingested",
        )
        assert concept.frontmatter.type == "policy"


class TestChatAgentWithLLM:
    @pytest.mark.asyncio
    async def test_calls_llm_when_context_found(self, tmp_path):
        from app.agents.chat import ChatAgent
        from app.storage.bundle import BundleManager
        from app.models.okf import OKFConcept, OKFFrontmatter

        bundle = BundleManager(str(tmp_path), "test_ws")
        mock_llm = MockLLMClient()

        concept = OKFConcept(
            filepath="test.md",
            frontmatter=OKFFrontmatter(type="reference", title="Test", tags=["test"]),
            body="# Test\n\nThis is test content about security policies.",
        )
        bundle.write_concept(concept)

        agent = ChatAgent(bundle, llm_client=mock_llm)
        result = await agent.answer("Tell me about security")

        assert result["answer"] == "Mocked response"
        assert len(result["citations"]) == 1
        assert result["citations"][0]["filepath"] == "test.md"

    @pytest.mark.asyncio
    async def test_no_context_returns_no_answer(self, tmp_path):
        from app.agents.chat import ChatAgent
        from app.storage.bundle import BundleManager

        bundle = BundleManager(str(tmp_path), "test_ws")
        mock_llm = MockLLMClient()

        agent = ChatAgent(bundle, llm_client=mock_llm)
        result = await agent.answer("Something not in knowledge base")

        assert "cannot answer" in result["answer"].lower()
        assert result["citations"] == []

    @pytest.mark.asyncio
    async def test_no_llm_fallback_returns_raw_prompt(self, tmp_path):
        from app.agents.chat import ChatAgent
        from app.storage.bundle import BundleManager
        from app.models.okf import OKFConcept, OKFFrontmatter

        bundle = BundleManager(str(tmp_path), "test_ws")
        concept = OKFConcept(
            filepath="test.md",
            frontmatter=OKFFrontmatter(type="reference", title="Test", tags=["test"]),
            body="# Test\n\nContent about security.",
        )
        bundle.write_concept(concept)

        agent = ChatAgent(bundle)
        result = await agent.answer("Tell me about security")

        assert "Retrieved Context" in result["answer"]
        assert len(result["citations"]) == 1


class TestLinkerAgentWithLLM:
    @pytest.mark.asyncio
    async def test_embedding_boosts_relevance(self, tmp_path):
        from app.agents.linker import LinkerAgent
        from app.storage.bundle import BundleManager
        from app.models.okf import OKFConcept, OKFFrontmatter

        bundle = BundleManager(str(tmp_path), "test_ws")

        existing = OKFConcept(
            filepath="ingested/security.md",
            frontmatter=OKFFrontmatter(type="policy", title="Security Policy", tags=["policy"]),
            body="# Security Policy\n\nAll security policies...",
        )
        bundle.write_concept(existing)

        new_concept = OKFConcept(
            filepath="ingested/new-concept.md",
            frontmatter=OKFFrontmatter(type="policy", title="New Concept", tags=["policy"]),
            body="# New Concept\n\nSome new content.",
        )

        mock_llm = MockLLMClient()
        agent = LinkerAgent(bundle, llm_client=mock_llm)
        linked, paths = await agent.link_concept(new_concept)

        assert "## See Also" in linked.body
        assert len(paths) > 0
        assert "ingested/security.md" in paths

    @pytest.mark.asyncio
    async def test_no_llm_still_links_keywords(self, tmp_path):
        from app.agents.linker import LinkerAgent
        from app.storage.bundle import BundleManager
        from app.models.okf import OKFConcept, OKFFrontmatter

        bundle = BundleManager(str(tmp_path), "test_ws")

        existing = OKFConcept(
            filepath="ingested/security.md",
            frontmatter=OKFFrontmatter(type="policy", title="Security Policy", tags=["policy", "security"]),
            body="# Security Policy\n\nAll employees must follow security policies.",
        )
        bundle.write_concept(existing)

        new_concept = OKFConcept(
            filepath="ingested/new-concept.md",
            frontmatter=OKFFrontmatter(type="policy", title="Security Guidelines", tags=["policy", "security"]),
            body="# Security Guidelines\n\nSome security content.",
        )

        agent = LinkerAgent(bundle)
        linked, paths = await agent.link_concept(new_concept)

        assert "## See Also" in linked.body
        assert "ingested/security.md" in paths
