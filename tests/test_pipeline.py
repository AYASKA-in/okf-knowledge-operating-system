"""Tests for pipeline orchestrator and stages."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.pipeline import PipelineOrchestrator, PipelineContext
from app.pipeline.stages import (
    ParseStage, ChunkStage, StructureStage, LinkStage, EmbedStage, IndexStage,
)
from app.pipeline.stages.base import StageError


class TestPipelineContext:
    def test_update_merges_data(self):
        ctx = PipelineContext()
        ctx.update("stage1", {"a": 1})
        ctx.update("stage2", {"b": 2})
        assert ctx.ctx["a"] == 1
        assert ctx.ctx["b"] == 2
        assert ctx.results["stage1"].success
        assert ctx.results["stage2"].success

    def test_fail_records_error(self):
        ctx = PipelineContext()
        ctx.fail("stage1", "Something broke")
        assert not ctx.results["stage1"].success
        assert "Something broke" in ctx.results["stage1"].error


@pytest.mark.asyncio
class TestParseStage:
    async def test_requires_file_data(self):
        stage = ParseStage()
        with pytest.raises(StageError):
            await stage.run({"filename": "test.md"})

    async def test_parse_csv(self):
        stage = ParseStage()
        result = await stage.run({
            "file_data": b"a,b\n1,2",
            "filename": "data.csv",
            "mime_hint": "",
        })
        assert result["source_type"] == "csv"
        assert "a" in result["raw_markdown"]


@pytest.mark.asyncio
class TestChunkStage:
    async def test_requires_markdown(self):
        stage = ChunkStage()
        with pytest.raises(StageError):
            await stage.run({})

    async def test_chunks_markdown(self):
        stage = ChunkStage()
        result = await stage.run({
            "raw_markdown": "# Title\n\nContent",
            "filename": "test.md",
            "source_type": "text",
        })
        assert "sections" in result
        assert len(result["sections"]) >= 1


@pytest.mark.asyncio
class TestStructureStage:
    async def test_empty_sections(self):
        stage = StructureStage()
        result = await stage.run({"sections": []})
        assert result["structured_count"] == 0

    async def test_structures_section(self):
        stage = StructureStage()
        result = await stage.run({
            "sections": [{
                "section_title": "Test Policy",
                "raw_text": "Employees must comply.",
                "hash": "abc123",
            }],
        })
        assert result["structured_count"] == 1
        assert result["concepts"][0].frontmatter.type is not None


@pytest.mark.asyncio
class TestEmbedStage:
    async def test_no_concepts_skips(self):
        stage = EmbedStage()
        result = await stage.run({"concepts": [], "workspace_id": "ws1"})
        assert result["vectors_indexed"] == 0

    async def test_no_llm_skips(self):
        stage = EmbedStage()
        result = await stage.run({
            "concepts": [MagicMock()],
            "workspace_id": "ws1",
            "use_vector_store": False,
        })
        assert result["embedding_skipped"]

    async def test_empty_concept_skips(self):
        stage = EmbedStage()
        concept = MagicMock()
        concept.frontmatter.title = ""
        concept.body = ""
        concept.filepath = "empty.md"
        result = await stage.run({
            "concepts": [concept],
            "workspace_id": "ws1",
            "use_vector_store": False,
        })
        assert result["vectors_indexed"] == 0


class TestIndexStage:
    def test_empty_concepts(self):
        from app.storage.bundle import BundleManager
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            bundle = BundleManager(tmp, "test_ws")
            stage = IndexStage(bundle)
            import asyncio
            result = asyncio.run(stage.run({"concepts": [], "filename": "test.md"}))
            assert result["concepts_written"] == 0


@pytest.mark.asyncio
class TestPipelineOrchestrator:
    async def test_run_empty_context(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with patch("app.config.settings.okf_bundle_root", tmp):
                orch = PipelineOrchestrator("test_ws")
                ctx = PipelineContext()
                ctx.ctx.update({
                    "file_data": b"# Title\n\nContent",
                    "filename": "test.md",
                    "mime_hint": "",
                    "workspace_id": "test_ws",
                    "raw_markdown": "# Title\n\nContent",
                    "source_type": "text",
                })
                result = await orch.run(ctx)
                assert "parse" in result.results
                assert "chunk" in result.results

    async def test_run_from_stage(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with patch("app.config.settings.okf_bundle_root", tmp):
                orch = PipelineOrchestrator("test_ws")
                ctx = PipelineContext()
                ctx.ctx.update({
                    "raw_markdown": "# Title\n\nBody",
                    "filename": "test.md",
                    "source_type": "text",
                    "workspace_id": "test_ws",
                })
                result = await orch.run_from_stage(ctx, start_at="chunk")
                assert "chunk" in result.results
