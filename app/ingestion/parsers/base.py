from abc import ABC, abstractmethod

from app.ingestion.models import ParsedDocument


class DocumentParser(ABC):
    @abstractmethod
    def parse(self, data: bytes, filename: str = "") -> ParsedDocument:
        ...
