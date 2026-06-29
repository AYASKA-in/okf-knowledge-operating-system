import logging
from typing import Any, Optional

from app.storage.bundle import BundleManager
from app.config import settings
from app.pipeline.stages import (
    ParseStage, ChunkStage, StructureStage,
    LinkStage, EmbedStage, IndexStage,
)

logger = logging.getLogger(__name__)


class StageResult:
    def __init__(self, stage: str, success: bool, data: dict, error: Optional[str] = None):
        self.stage = stage
        self.success = success
        self.data = data
        self.error = error


class PipelineContext:
    def __init__(self):
        self.results: dict[str, StageResult] = {}
        self.ctx: dict[str, Any] = {}

    def update(self, stage: str, data: dict):
        self.ctx.update(data)
        self.results[stage] = StageResult(stage=stage, success=True, data=data)

    def fail(self, stage: str, error: str):
        self.results[stage] = StageResult(stage=stage, success=False, data={}, error=error)


class PipelineOrchestrator:
    def __init__(self, workspace_id: str, llm_client=None):
        self.workspace_id = workspace_id
        self._llm = llm_client
        self.bundle = BundleManager(settings.okf_bundle_root, workspace_id)

    def build_pipeline(self) -> list:
        return [
            ("parse", ParseStage()),
            ("chunk", ChunkStage(llm_client=self._llm)),
            ("structure", StructureStage(llm_client=self._llm)),
            ("link", LinkStage(self.bundle, llm_client=self._llm)),
            ("embed", EmbedStage(llm_client=self._llm)),
            ("index", IndexStage(self.bundle)),
        ]

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        stages = self.build_pipeline()

        for name, stage in stages:
            try:
                logger.info("Pipeline stage [%s] starting", name)
                result = await stage.run(ctx.ctx)
                ctx.update(name, result)
                logger.info("Pipeline stage [%s] completed", name)
            except Exception as e:
                error_msg = f"{type(e).__name__}: {e}"
                logger.error("Pipeline stage [%s] failed: %s", name, error_msg)
                ctx.fail(name, error_msg)

        return ctx

    async def run_from_stage(self, ctx: PipelineContext, start_at: str) -> PipelineContext:
        stages = self.build_pipeline()
        started = False

        for name, stage in stages:
            if not started and name != start_at:
                continue
            started = True

            try:
                logger.info("Pipeline stage [%s] starting (resumed)", name)
                result = await stage.run(ctx.ctx)
                ctx.update(name, result)
                logger.info("Pipeline stage [%s] completed", name)
            except Exception as e:
                error_msg = f"{type(e).__name__}: {e}"
                logger.error("Pipeline stage [%s] failed: %s", name, error_msg)
                ctx.fail(name, error_msg)

        return ctx
