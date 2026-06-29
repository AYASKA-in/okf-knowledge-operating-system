import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

from app.ingestion.models import ParsedDocument, Section
from app.ingestion.parsers.base import DocumentParser


class NotionParser(DocumentParser):
    def parse(self, data: bytes, filename: str = "") -> ParsedDocument:
        text = data.decode("utf-8")
        title = Path(filename).stem if filename else "Untitled Notion Export"

        stripped = text.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            return self._parse_json(text, title, filename)
        return self._parse_html(text, title, filename)

    def _parse_json(self, text: str, title: str, filename: str) -> ParsedDocument:
        data = json.loads(text)
        pages = data if isinstance(data, list) else [data]
        all_sections: list[Section] = []

        for page in pages:
            page_title = (
                page.get("title")
                or page.get("properties", {}).get("title", {}).get("title", [{}])[0].get("plain_text", "")
                or title
            )
            blocks = page.get("blocks") or page.get("content") or page.get("children", [])
            md = self._blocks_to_markdown(blocks)
            all_sections.append(Section(title=page_title, text=md))

        return ParsedDocument(
            title=title,
            sections=all_sections if all_sections else [Section(title=title, text="")],
            source_type="notion_json",
            metadata={"filename": filename, "page_count": len(pages)},
        )

    def _parse_html(self, text: str, title: str, filename: str) -> ParsedDocument:
        soup = BeautifulSoup(text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()

        sections: list[Section] = []
        current_title = title
        current_lines: list[str] = []

        for el in soup.find_all(["h1", "h2", "h3", "p", "ul", "ol", "pre", "blockquote", "hr"]):
            tag = el.name
            if tag in ("h1", "h2", "h3"):
                if current_lines:
                    sections.append(Section(title=current_title, text="\n".join(current_lines).strip()))
                current_title = el.get_text(strip=True)
                current_lines = [current_title]
            elif tag in ("p", "blockquote"):
                current_lines.append(el.get_text(strip=True))
            elif tag in ("ul", "ol"):
                for li in el.find_all("li"):
                    current_lines.append(f"- {li.get_text(strip=True)}")
            elif tag == "pre":
                code = el.get_text("\n", strip=True)
                current_lines.append(f"```\n{code}\n```")
            elif tag == "hr":
                current_lines.append("---")

        if current_lines:
            sections.append(Section(title=current_title, text="\n".join(current_lines).strip()))

        return ParsedDocument(
            title=title,
            sections=[s for s in sections if s.text],
            source_type="notion_html",
            metadata={"filename": filename},
        )

    def _blocks_to_markdown(self, blocks: list, indent: int = 0) -> str:
        lines: list[str] = []
        prefix = "  " * indent

        for block in blocks:
            btype = block.get("type", "")
            content = block.get("content", block.get("text", ""))
            if isinstance(content, list):
                content = " ".join(
                    c.get("plain_text", c.get("text", "")) if isinstance(c, dict) else str(c)
                    for c in content
                )
            content = str(content).strip()

            if btype in ("heading_1", "heading_2", "heading_3"):
                level = btype[-1]
                lines.append(f"{prefix}{'#' * int(level)} {content}")
            elif btype in ("paragraph",):
                lines.append(f"{prefix}{content}" if content else "")
            elif btype in ("bulleted_list_item",):
                lines.append(f"{prefix}- {content}")
            elif btype in ("numbered_list_item",):
                lines.append(f"{prefix}1. {content}")
            elif btype in ("to_do",):
                checked = block.get("checked", False)
                marker = "[x]" if checked else "[ ]"
                lines.append(f"{prefix}- {marker} {content}")
            elif btype in ("code",):
                lang = block.get("language", "")
                lines.append(f"{prefix}```{lang}\n{prefix}{content}\n{prefix}```")
            elif btype in ("quote", "callout"):
                lines.append(f"{prefix}> {content}")
            elif btype == "divider":
                lines.append(f"{prefix}---")
            elif btype == "image":
                caption = block.get("caption", "")
                lines.append(f"{prefix}![{caption}]({content})")
            elif btype == "table":
                table_lines = self._notion_table_to_md(block)
                lines.extend(table_lines)

            children = block.get("children", [])
            if children:
                nested = self._blocks_to_markdown(children, indent + 1)
                if nested:
                    lines.append(nested)

        return "\n".join(lines)

    def _notion_table_to_md(self, block: dict) -> list[str]:
        rows = block.get("rows", block.get("children", []))
        if not rows:
            return []
        md_rows: list[str] = []
        for i, row in enumerate(rows):
            cells = row.get("cells", [])
            cell_texts = []
            for cell in cells:
                if isinstance(cell, list):
                    cell_texts.append(
                        " ".join(c.get("plain_text", "") for c in cell)
                    )
                elif isinstance(cell, dict):
                    cell_texts.append(cell.get("plain_text", ""))
                else:
                    cell_texts.append(str(cell))
            md_rows.append("| " + " | ".join(cell_texts) + " |")
            if i == 0:
                md_rows.append("| " + " | ".join("---" for _ in cell_texts) + " |")
        return md_rows
