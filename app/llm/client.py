import logging
from functools import lru_cache
from typing import List, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class VertexAIClient:
    def __init__(self):
        self._initialized = False

    def _ensure_initialized(self):
        if self._initialized:
            return
        if not settings.gcp_project_id:
            logger.warning("gcp_project_id not set; LLM calls will return fallback responses")
            self._initialized = True
            return
        try:
            import vertexai
            vertexai.init(
                project=settings.gcp_project_id,
                location=settings.vertex_ai_location,
            )
            self._initialized = True
        except Exception:
            logger.exception("Failed to initialize Vertex AI; LLM calls will fall back")
            self._initialized = True

    def generate_text(self, prompt: str, model_name: Optional[str] = None,
                      temperature: float = 0.2, max_tokens: int = 4096) -> str:
        self._ensure_initialized()
        if not settings.gcp_project_id:
            return self._fallback_generate(prompt)
        try:
            from vertexai.generative_models import GenerationConfig, GenerativeModel
            model = GenerativeModel(model_name or settings.ingestion_model)
            response = model.generate_content(
                prompt,
                generation_config=GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )
            return response.text
        except Exception:
            logger.exception("Vertex AI generation failed; falling back")
            return self._fallback_generate(prompt)

    async def generate_text_async(self, prompt: str, model_name: Optional[str] = None,
                                   temperature: float = 0.2, max_tokens: int = 4096) -> str:
        self._ensure_initialized()
        if not settings.gcp_project_id:
            return self._fallback_generate(prompt)
        try:
            from vertexai.generative_models import GenerationConfig, GenerativeModel
            model = GenerativeModel(model_name or settings.ingestion_model)
            response = await model.generate_content_async(
                prompt,
                generation_config=GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )
            return response.text
        except Exception:
            logger.exception("Vertex AI async generation failed; falling back")
            return self._fallback_generate(prompt)

    def embed_text(self, text: str) -> List[float]:
        self._ensure_initialized()
        if not settings.gcp_project_id:
            return self._fallback_embedding(text)
        try:
            from vertexai.language_models import TextEmbeddingModel
            model = TextEmbeddingModel.from_pretrained(settings.embedding_model)
            embeddings = model.get_embeddings([text[:2000]])
            return embeddings[0].values
        except Exception:
            logger.exception("Vertex AI embedding failed; falling back")
            return self._fallback_embedding(text)

    def _fallback_generate(self, prompt: str) -> str:
        return ""

    def _fallback_embedding(self, text: str) -> List[float]:
        return []


@lru_cache
def get_llm_client() -> VertexAIClient:
    return VertexAIClient()
