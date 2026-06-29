from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
import re


class OKFFrontmatter(BaseModel):
    type: str
    title: Optional[str] = None
    description: Optional[str] = None
    resource: Optional[str] = None
    tags: Optional[List[str]] = None
    timestamp: Optional[str] = None
    status: Optional[str] = "draft"
    source_hash: Optional[str] = None
    author: Optional[str] = None

    @field_validator("timestamp", mode="before")
    @classmethod
    def coerce_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    def to_yaml_dict(self) -> dict:
        d = {"type": self.type}
        for key in ("title", "description", "resource", "tags", "timestamp",
                     "status", "source_hash", "author"):
            val = getattr(self, key, None)
            if val is not None:
                d[key] = val
        return d


class OKFConcept(BaseModel):
    filepath: str
    frontmatter: OKFFrontmatter
    body: str

    def to_markdown(self) -> str:
        import yaml
        fm_dict = self.frontmatter.to_yaml_dict()
        fm_yaml = yaml.dump(fm_dict, default_flow_style=False, allow_unicode=True).strip()
        return f"---\n{fm_yaml}\n---\n\n{self.body.strip()}\n"

    @classmethod
    def from_markdown(cls, filepath: str, content: str) -> "OKFConcept":
        import yaml
        parts = content.split("---", 2)
        if len(parts) < 3:
            raise ValueError(f"Invalid OKF markdown in {filepath}: missing frontmatter")
        fm_data = yaml.safe_load(parts[1])
        frontmatter = OKFFrontmatter(**fm_data)
        body = parts[2].strip()
        return cls(filepath=filepath, frontmatter=frontmatter, body=body)

    def extract_links(self) -> List[str]:
        md_link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
        return [match.group(2) for match in md_link_pattern.finditer(self.body)]


class OKFBundle(BaseModel):
    root_path: str
    workspace_id: str
    concepts: List[OKFConcept] = Field(default_factory=list)

    def has_index(self) -> bool:
        import os
        return os.path.exists(os.path.join(self.root_path, "index.md"))

    def has_log(self) -> bool:
        import os
        return os.path.exists(os.path.join(self.root_path, "log.md"))
