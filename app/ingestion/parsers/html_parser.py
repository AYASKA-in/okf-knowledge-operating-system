from pathlib import Path

from bs4 import BeautifulSoup

from app.ingestion.models import ParsedDocument, Section
from app.ingestion.parsers.base import DocumentParser


class HtmlParser(DocumentParser):
    def parse(self, data: bytes, filename: str = "") -> ParsedDocument:
        soup = BeautifulSoup(data, "html.parser")

        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else Path(filename).stem if filename else "Untitled HTML"

        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        sections: list[Section] = []
        current_title = title
        current_lines: list[str] = []

        body = soup.find("body") or soup
        for el in body.children:
            if not hasattr(el, "name") or el.name is None:
                continue
            tag_name = el.name.lower()
            text = el.get_text(" ", strip=True)
            if not text:
                continue
            if tag_name in ("h1", "h2", "h3", "h4"):
                if current_lines:
                    sections.append(Section(title=current_title, text="\n".join(current_lines).strip()))
                current_title = text
                current_lines = [text]
            elif tag_name in ("p", "li", "td", "th", "blockquote", "pre", "div"):
                current_lines.append(text)

        if current_lines:
            sections.append(Section(title=current_title, text="\n".join(current_lines).strip()))

        return ParsedDocument(
            title=title,
            sections=[s for s in sections if s.text],
            source_type="html",
            metadata={"filename": filename},
        )
