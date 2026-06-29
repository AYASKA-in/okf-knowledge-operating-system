import re


class MarkdownCleaner:
    def clean(self, text: str) -> str:
        text = self._normalize_newlines(text)
        text = self._strip_boilerplate(text)
        text = self._normalize_headings(text)
        text = self._compact_whitespace(text)
        return text.strip()

    def _normalize_newlines(self, text: str) -> str:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"\n{4,}", "\n\n\n", text)
        return text

    def _strip_boilerplate(self, text: str) -> str:
        patterns = [
            r"^---\s*\n.*?\n---\s*\n",
            r"(?i)^#\s*table\s+of\s+contents\s*\n.*?(?=\n#|\Z)",
            r"(?i)^#\s*introduction\s*\n(?:\s*[^.]+\.\s*\n){1,3}",
            r"<!--.*?-->",
            r"\[//\]:\s*#\s*\(.*?\)",
        ]
        for pat in patterns:
            text = re.sub(pat, "", text, count=1, flags=re.DOTALL)
        return text

    def _normalize_headings(self, text: str) -> str:
        lines = text.split("\n")
        result: list[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped and re.match(r"^[A-Z][A-Z\s\-]{3,}$", stripped) and len(stripped) < 80:
                line = "## " + stripped
            result.append(line)
        return "\n".join(result)

    def _compact_whitespace(self, text: str) -> str:
        text = re.sub(r" {2,}", " ", text)
        text = re.sub(r"\n\s{3,}\n", "\n\n", text)
        lines = text.split("\n")
        compacted: list[str] = []
        for line in lines:
            if line.strip() or (compacted and compacted[-1].strip()):
                compacted.append(line.strip() if line.strip() == "" else line)
        return "\n".join(compacted)
