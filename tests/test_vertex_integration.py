"""Gated integration tests for Vertex AI.

Requires GCP_PROJECT_ID env var and valid GCP credentials.
"""
import os
import pytest
from app.config import settings
from app.llm.client import VertexAIClient

skip_no_gcp = pytest.mark.skipif(
    not os.environ.get("GCP_PROJECT_ID") and not os.environ.get("GCP_PROJECT"),
    reason="GCP credentials not configured",
)


@pytest.fixture
def llm_client():
    project_id = os.environ.get("GCP_PROJECT_ID") or os.environ.get("GCP_PROJECT") or ""
    settings.gcp_project_id = project_id
    return VertexAIClient()


class TestVertexRealLLM:
    @skip_no_gcp
    @pytest.mark.asyncio
    async def test_generate_text_real(self, llm_client):
        result = await llm_client.generate_text_async("Say 'hello' in one word")
        assert isinstance(result, str)
        assert len(result) > 0

    @skip_no_gcp
    @pytest.mark.asyncio
    async def test_embed_text_real(self, llm_client):
        result = await llm_client.embed_text_async("test query")
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(v, float) for v in result)

    @skip_no_gcp
    @pytest.mark.asyncio
    async def test_embedding_dimension(self, llm_client):
        result = await llm_client.embed_text_async("test")
        assert len(result) == 768

    @skip_no_gcp
    def test_sync_embed_text(self, llm_client):
        result = llm_client.embed_text("test query")
        assert isinstance(result, list)
        assert len(result) > 0
