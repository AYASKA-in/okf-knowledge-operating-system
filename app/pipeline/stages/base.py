from abc import ABC, abstractmethod
from typing import Any, Optional


class StageError(Exception):
    def __init__(self, message: str, stage: str, recoverable: bool = True):
        self.stage = stage
        self.recoverable = recoverable
        super().__init__(message)


class PipelineStage(ABC):
    name: str = ""

    @abstractmethod
    async def run(self, ctx: dict[str, Any]) -> dict[str, Any]:
        ...
