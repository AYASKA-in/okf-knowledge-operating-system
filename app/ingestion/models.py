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
