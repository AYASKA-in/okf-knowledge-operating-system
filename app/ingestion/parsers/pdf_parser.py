from pathlib import Path

import pdfplumber

from app.ingestion.models import ParsedDocument, Section
from app.ingestion.parsers.base import DocumentParser


class PdfParser(DocumentParser):
    def parse(self, data: bytes, filename: str = "") -> ParsedDocument:
        import io
        title = Path(filename).stem if filename else "Untitled PDF"

        with pdfplumber.open(io.BytesIO(data)) as pdf:
            text_pages: list[str] = []
            for page in pdf.pages:
                txt = page.extract_text()
                if txt:
                    text_pages.append(txt)

        full_text = "\n\n".join(text_pages)
        sections = self._to_sections(full_text, title)
        return ParsedDocument(
            title=title,
            sections=sections,
            source_type="pdf",
            metadata={"pages": len(pdf.pages), "filename": filename},
        )

    def _to_sections(self, text: str, fallback_title: str) -> list[Section]:
        import re
        lines = text.split("\n")
        sections: list[Section] = []
        current_title = fallback_title
        current_lines: list[str] = []

        heading = re.compile(r"^(#{1,3}\s+)?([A-Z][A-Z\s\-]{2,}|[A-Z][a-z]+(\s[A-Z][a-z]+)*)$")

        for line in lines:
            stripped = line.strip()
            if not stripped:
                current_lines.append("")
                continue
            m = heading.match(stripped)
            if m and len(stripped) < 100 and stripped[-1] not in ".:;,":
                if current_lines:
                    sections.append(Section(title=current_title, text="\n".join(current_lines).strip()))
                current_title = stripped.lstrip("# ")
                current_lines = [line]
            else:
                current_lines.append(line)

        if current_lines:
            sections.append(Section(title=current_title, text="\n".join(current_lines).strip()))

        return [s for s in sections if s.text]
