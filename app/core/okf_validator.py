import os
import yaml
import re
from pathlib import Path
from typing import List, Optional


class ValidationResult:
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def merge(self, other: "ValidationResult") -> "ValidationResult":
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        return self

    def __repr__(self) -> str:
        return f"ValidationResult(valid={self.is_valid}, errors={len(self.errors)}, warnings={len(self.warnings)})"


RESERVED_FILENAMES = {"index.md", "log.md"}
REQUIRED_FM_FIELD = "type"
VALID_MD_LINK = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
WIKI_LINK = re.compile(r'\[\[([^\]]+)\]\]')


class OKFValidator:
    def validate_bundle(self, root_path: str) -> ValidationResult:
        result = ValidationResult()
        if not os.path.isdir(root_path):
            result.errors.append(f"Bundle root not found: {root_path}")
            return result

        has_index = os.path.exists(os.path.join(root_path, "index.md"))
        has_log = os.path.exists(os.path.join(root_path, "log.md"))
        if not has_index:
            result.warnings.append(f"Bundle missing index.md at root")
        if not has_log:
            result.warnings.append(f"Bundle missing log.md at root")

        for dirpath, dirnames, filenames in os.walk(root_path):
            for fn in filenames:
                if not fn.endswith(".md"):
                    continue
                full_path = os.path.join(dirpath, fn)
                rel_path = os.path.relpath(full_path, root_path)
                file_result = self.validate_file(full_path, rel_path)
                result.merge(file_result)

        return result

    def validate_file(self, full_path: str, rel_path: str) -> ValidationResult:
        result = ValidationResult()
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            result.errors.append(f"{rel_path}: cannot read file: {e}")
            return result

        if not content.startswith("---"):
            result.errors.append(f"{rel_path}: missing YAML frontmatter (must start with '---')")
            return result

        parts = content.split("---", 2)
        if len(parts) < 3:
            result.errors.append(f"{rel_path}: malformed frontmatter (unclosed '---' delimiter)")
            return result

        try:
            fm = yaml.safe_load(parts[1])
        except yaml.YAMLError as e:
            result.errors.append(f"{rel_path}: invalid YAML frontmatter: {e}")
            return result

        if not isinstance(fm, dict):
            result.errors.append(f"{rel_path}: frontmatter must be a mapping")
            return result

        if REQUIRED_FM_FIELD not in fm:
            result.errors.append(f"{rel_path}: missing required frontmatter field '{REQUIRED_FM_FIELD}'")

        body = parts[2].strip()
        self._check_wiki_links(body, rel_path, result)
        self._check_md_links(body, rel_path, result)

        return result

    def _check_wiki_links(self, body: str, rel_path: str, result: ValidationResult):
        matches = WIKI_LINK.findall(body)
        if matches:
            result.errors.append(
                f"{rel_path}: found forbidden wiki-style links [[...]]: {matches[:3]}. "
                f"Use standard Markdown links [text](./path.md) instead."
            )

    def _check_md_links(self, body: str, rel_path: str, result: ValidationResult):
        matches = VALID_MD_LINK.findall(body)
        for text, target in matches:
            if target.startswith("http://") or target.startswith("https://"):
                continue
            if target.startswith("#"):
                continue
            if not self._looks_like_valid_path(target):
                result.warnings.append(
                    f"{rel_path}: link target may be invalid: '{target}'"
                )

    def _looks_like_valid_path(self, path: str) -> bool:
        if path.startswith("./") or path.startswith("../"):
            return True
        if "/" in path or path.endswith(".md"):
            return True
        return False
