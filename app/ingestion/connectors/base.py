from abc import ABC, abstractmethod
from typing import Optional

from app.ingestion.models import ParsedDocument


class DocumentConnector(ABC):
    connector_type: str = ""

    @abstractmethod
    async def fetch(self, config: dict) -> list[ParsedDocument]:
        ...

    @abstractmethod
    async def validate_config(self, config: dict) -> str:
        """Validate config and return a human-readable status message."""
        ...
