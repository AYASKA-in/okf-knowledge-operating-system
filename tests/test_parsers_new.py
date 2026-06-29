"""Tests for CSV, Notion parsers and MarkdownCleaner."""
import io
import pytest

from app.ingestion.parsers.csv_parser import CsvParser
from app.ingestion.parsers.notion_parser import NotionParser
from app.ingestion.cleaner import MarkdownCleaner
from app.ingestion.router import IngestionRouter


class TestCsvParser:
    def test_parse_simple_csv(self):
        data = b"Name,Age,City\nAlice,30,New York\nBob,25,London"
        parser = CsvParser()
        doc = parser.parse(data, filename="data.csv")
        assert doc.title == "data"
        assert doc.source_type == "csv"
        assert len(doc.sections) == 1
        assert "Alice" in doc.sections[0].text
        assert "Bob" in doc.sections[0].text

    def test_parse_csv_with_pipe_separator(self):
        data = b"Name,Age\nAlice,30\nBob,25"
        parser = CsvParser()
        doc = parser.parse(data, filename="test.csv")
        text = doc.sections[0].text
        assert "| Name | Age |" in text
        assert "| --- | --- |" in text
        assert "| Alice | 30 |" in text

    def test_parse_csv_empty(self):
        parser = CsvParser()
        doc = parser.parse(b"", filename="empty.csv")
        assert doc.source_type == "csv"
        assert len(doc.sections) == 0

    def test_parse_csv_utf8_bom(self):
        data = b"\xef\xbb\xbfName,City\nAlice,NYC"
        parser = CsvParser()
        doc = parser.parse(data, filename="bom.csv")
        assert "Alice" in doc.sections[0].text


class TestNotionParser:
    def test_parse_notion_html(self):
        html = b"""<html><head><title>Notion Export</title></head>
        <body><h1>Project Plan</h1><p>This is the plan.</p>
        <h2>Timeline</h2><p>Q1 2026</p></body></html>"""
        parser = NotionParser()
        doc = parser.parse(html, filename="export.html")
        assert doc.source_type == "notion_html"
        assert len(doc.sections) >= 1

    def test_parse_notion_json(self):
        data = b'[{"title":"Page 1","blocks":[{"type":"heading_1","text":"Hello"},{"type":"paragraph","text":"World"}]}]'
        parser = NotionParser()
        doc = parser.parse(data, filename="export.json")
        assert doc.source_type == "notion_json"
        assert len(doc.sections) >= 1

    def test_parse_notion_json_single(self):
        data = b'{"title":"Single Page","blocks":[{"type":"heading_1","text":"Title"},{"type":"paragraph","text":"Body"}]}'
        parser = NotionParser()
        doc = parser.parse(data, filename="single.json")
        assert doc.source_type == "notion_json"

    def test_notion_parser_detected_via_router(self):
        router = IngestionRouter()
        mime = router.detect(b"{}", filename="export.json")
        assert mime == "application/json"


class TestMarkdownCleaner:
    def test_normalize_newlines(self):
        cleaner = MarkdownCleaner()
        assert cleaner.clean("a\r\nb\r\nc") == "a\nb\nc"

    def test_strip_html_comments(self):
        cleaner = MarkdownCleaner()
        result = cleaner.clean("# Title\n\n<!-- comment -->\n\nBody")
        assert "<!--" not in result
        assert "Body" in result

    def test_heading_normalization(self):
        cleaner = MarkdownCleaner()
        text = "IMPORTANT NOTICE\n\nThis is a notice."
        result = cleaner.clean(text)
        assert "## IMPORTANT NOTICE" in result

    def test_compact_whitespace(self):
        cleaner = MarkdownCleaner()
        text = "Line1\n\n\n\n\nLine2"
        result = cleaner.clean(text)
        assert "\n\n\n" not in result

    def test_cleaner_roundtrip(self):
        cleaner = MarkdownCleaner()
        md = "# Title\n\nParagraph text.\n\n## Subtitle\n\nMore text."
        result = cleaner.clean(md)
        assert "Title" in result
        assert "Paragraph" in result

    def test_strip_toc(self):
        cleaner = MarkdownCleaner()
        text = "# Table of Contents\n\n- Intro\n- Details\n\n# Real Content\n\nBody"
        result = cleaner.clean(text)
        assert "Real Content" in result


class TestIngestionRouter:
    def test_route_csv(self):
        router = IngestionRouter()
        data = b"a,b,c\n1,2,3"
        doc = router.route(data, filename="data.csv")
        assert doc.source_type == "csv"

    def test_route_pdf(self):
        from reportlab.pdfgen import canvas
        import io
        buf = io.BytesIO()
        c = canvas.Canvas(buf)
        c.drawString(100, 700, "Test")
        c.save()
        router = IngestionRouter()
        doc = router.route(buf.getvalue(), filename="doc.pdf")
        assert doc.source_type == "pdf"

    def test_route_unsupported_raises(self):
        router = IngestionRouter()
        with pytest.raises(ValueError, match="Unsupported format"):
            router.route(b"\x00\x01\x02\x03", filename="data.bin")

    def test_supported_types(self):
        router = IngestionRouter()
        types = router.supported_types()
        assert "text/csv" in types
        assert "application/pdf" in types
