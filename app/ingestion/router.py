from app.ingestion.models import ParsedDocument
from app.ingestion.parsers import detect_format, parse_document


class IngestionRouter:
    def route(self, data: bytes, filename: str = "", mime_hint: str = "") -> ParsedDocument:
        return parse_document(data, filename=filename, mime_hint=mime_hint)

    def detect(self, data: bytes, filename: str = "", mime_hint: str = "") -> str:
        return detect_format(data, filename=filename, mime_hint=mime_hint)

    def supported_types(self) -> list[str]:
        from app.ingestion.parsers import _REGISTRY
        return list(_REGISTRY.keys())
