import os
from typing import Optional

from app.ingestion.models import ParsedDocument
from app.ingestion.parsers.base import DocumentParser
from app.ingestion.parsers.pdf_parser import PdfParser
from app.ingestion.parsers.docx_parser import DocxParser
from app.ingestion.parsers.xlsx_parser import XlsxParser
from app.ingestion.parsers.html_parser import HtmlParser


_REGISTRY: dict[str, type[DocumentParser]] = {
    "application/pdf": PdfParser,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocxParser,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": XlsxParser,
    "text/html": HtmlParser,
}

_EXTENSION_MAP: dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".html": "text/html",
    ".htm": "text/html",
}

def _looks_like_html(data: bytes) -> bool:
    head = data[:500].lower()
    return (
        b"<html" in head
        or b"<!doctype html" in head
        or b"<!doctype h" in head
    )


def _detect_by_magic(data: bytes) -> Optional[str]:
    if data[:4] == b"%PDF":
        return "application/pdf"
    if data[:2] == b"PK":
        return None
    if _looks_like_html(data):
        return "text/html"
    return None


def detect_format(data: bytes, filename: str = "", mime_hint: str = "") -> str:
    if mime_hint and mime_hint in _REGISTRY:
        return mime_hint

    ext = os.path.splitext(filename)[1].lower()
    if ext in _EXTENSION_MAP:
        return _EXTENSION_MAP[ext]

    mime = _detect_by_magic(data)
    if mime and mime in _REGISTRY:
        return mime

    if b"PK" in data[:4]:
        if b"word" in data[30:100] or b"docx" in data[30:100]:
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if b"xl" in data[30:100]:
            return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    if b"<html" in data[:200] or b"<!DOCTYPE h" in data[:200]:
        return "text/html"

    return ""


def parse_document(data: bytes, filename: str = "", mime_hint: str = "") -> ParsedDocument:
    mime = detect_format(data, filename, mime_hint)
    if not mime:
        raise ValueError(
            f"Unsupported format. Recognised: {list(_REGISTRY.keys())}. "
            f"filename={filename!r}, mime_hint={mime_hint!r}"
        )
    parser_cls = _REGISTRY.get(mime)
    if not parser_cls:
        raise ValueError(f"No parser for MIME type {mime}")
    return parser_cls().parse(data, filename=filename)
