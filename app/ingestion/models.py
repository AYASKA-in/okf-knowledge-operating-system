from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Section:
    title: str
    text: str


@dataclass
class ParsedDocument:
    title: str
    sections: list[Section]
    source_type: str
    metadata: dict = field(default_factory=dict)

    @property
    def raw_markdown(self) -> str:
        return "\n\n".join(
            f"# {s.title}\n\n{s.text}" if not s.text.startswith("#") else s.text
            for s in self.sections
        )
