import csv
import io
from pathlib import Path

from app.ingestion.models import ParsedDocument, Section
from app.ingestion.parsers.base import DocumentParser


class CsvParser(DocumentParser):
    def parse(self, data: bytes, filename: str = "") -> ParsedDocument:
        title = Path(filename).stem if filename else "Untitled CSV"
        text = data.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text))

        rows = list(reader)
        if not rows:
            return ParsedDocument(title=title, sections=[], source_type="csv", metadata={"filename": filename})

        header = rows[0]
        col_count = len(header)
        md_lines = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in range(col_count)) + " |"]

        for row in rows[1:]:
            padded = row + [""] * (col_count - len(row))
            md_lines.append("| " + " | ".join(padded) + " |")

        table_text = "\n".join(md_lines)
        sections = [Section(title=title, text=table_text)]

        return ParsedDocument(
            title=title,
            sections=sections,
            source_type="csv",
            metadata={"filename": filename, "rows": len(rows), "columns": col_count},
        )
