from typing import Optional
from app.ingestion.models import ParsedDocument, Section
from app.ingestion.connectors.base import DocumentConnector


class NotionConnector(DocumentConnector):
    connector_type = "notion"

    async def fetch(self, config: dict) -> list[ParsedDocument]:
        import os
        os.environ["NOTION_TOKEN"] = config.get("token", "")

        from notion_client import Client
        client = Client(auth=config.get("token", ""))

        database_id = config.get("database_id", "")
        if not database_id:
            return []

        docs: list[ParsedDocument] = []

        pages = client.databases.query(database_id=database_id)
        for page in pages.get("results", []):
            props = page.get("properties", {})
            title = self._extract_title(props) or page["id"][:8]
            content_blocks = client.blocks.children.list(block_id=page["id"])
            sections = self._blocks_to_sections(content_blocks.get("results", []))

            docs.append(ParsedDocument(
                title=title,
                sections=sections,
                source_type="notion",
                metadata={"page_id": page["id"], "notion_url": page.get("url", "")},
            ))

        return docs

    async def validate_config(self, config: dict) -> str:
        from notion_client import Client
        try:
            client = Client(auth=config.get("token", ""))
            client.users.list_me()
            return "ok"
        except Exception as e:
            return f"Invalid Notion config: {e}"

    def _extract_title(self, props: dict) -> Optional[str]:
        for prop in props.values():
            if prop.get("type") == "title":
                texts = prop.get("title", [])
                if texts:
                    return "".join(t.get("plain_text", "") for t in texts)
        return None

    def _blocks_to_sections(self, blocks: list[dict]) -> list[Section]:
        sections: list[Section] = []
        current_title = "Untitled"
        current_lines: list[str] = []

        heading_types = {
            "heading_1": "h1", "heading_2": "h2", "heading_3": "h3",
        }

        for block in blocks:
            btype = block.get("type", "")
            if btype in heading_types:
                if current_lines:
                    sections.append(Section(title=current_title, text="\n".join(current_lines).strip()))
                rich = block.get(btype, {}).get("rich_text", [])
                current_title = "".join(r.get("plain_text", "") for r in rich)
                current_lines = [current_title]
            else:
                text = self._extract_block_text(block)
                if text:
                    current_lines.append(text)

        if current_lines:
            sections.append(Section(title=current_title, text="\n".join(current_lines).strip()))

        return [s for s in sections if s.text]

    def _extract_block_text(self, block: dict) -> str:
        btype = block.get("type", "")
        if btype in ("paragraph", "bulleted_list_item", "numbered_list_item", "quote", "to_do", "callout"):
            rich = block.get(btype, {}).get("rich_text", [])
            return "".join(r.get("plain_text", "") for r in rich)
        if btype == "code":
            rich = block.get("code", {}).get("rich_text", [])
            lang = block.get("code", {}).get("language", "")
            text = "".join(r.get("plain_text", "") for r in rich)
            return f"```{lang}\n{text}\n```"
        if btype == "divider":
            return "---"
        if btype == "image":
            caption = block.get("image", {}).get("caption", [{}])
            alt = "".join(c.get("plain_text", "") for c in caption) if isinstance(caption, list) else ""
            return f"[Image: {alt}]" if alt else "[Image]"
        if btype == "table":
            return self._extract_table_text(block)
        return ""

    def _extract_table_text(self, block: dict) -> str:
        rows = []
        table = block.get("table", {})
        for row_block in table.get("children", []):
            cells = row_block.get("table_row", {}).get("cells", [])
            row_text = " | ".join(
                "".join(c.get("plain_text", "") for c in cell)
                for cell in cells
            )
            rows.append(row_text)
        return "\n".join(rows)
