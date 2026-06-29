import os
import shutil
import hashlib
import logging
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple
from app.models.okf import OKFConcept, OKFFrontmatter, OKFBundle
from app.core.okf_validator import OKFValidator

logger = logging.getLogger(__name__)


class BundleError(Exception):
    pass


class BundleManager:
    def __init__(self, bundle_root: str, workspace_id: str):
        self.bundle_root = Path(bundle_root)
        self.workspace_id = workspace_id
        self.workspace_path = self.bundle_root / workspace_id
        self.validator = OKFValidator()
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        self._ensure_reserved_files()

    def _ensure_reserved_files(self):
        index_path = self.workspace_path / "index.md"
        if not index_path.exists():
            index_path.write_text(
                f"---\ntype: directory\n"
                f"title: {self.workspace_id}\n"
                f"description: Root index for workspace {self.workspace_id}\n"
                f"timestamp: {datetime.now(timezone.utc).isoformat()}\n"
                f"---\n\n"
                f"# {self.workspace_id}\n\n"
                f"This is the root of the OKF bundle for **{self.workspace_id}**.\n",
                encoding="utf-8"
            )

        log_path = self.workspace_path / "log.md"
        if not log_path.exists():
            log_path.write_text(
                f"---\ntype: audit_log\n"
                f"title: Change Log\n"
                f"description: Chronological audit trail for workspace {self.workspace_id}\n"
                f"timestamp: {datetime.now(timezone.utc).isoformat()}\n"
                f"---\n\n"
                f"# Change Log\n\n"
                f"| Timestamp | Action | File | Author |\n"
                f"|-----------|--------|------|--------|\n",
                encoding="utf-8"
            )

    def resolve_path(self, concept_path: str) -> Path:
        if concept_path.startswith("/"):
            concept_path = concept_path.lstrip("/")
        full = (self.workspace_path / concept_path).resolve()
        if not str(full).startswith(str(self.workspace_path.resolve())):
            raise BundleError("Path traversal detected")
        return full

    def write_concept(self, concept: OKFConcept) -> Path:
        target = self.resolve_path(concept.filepath)
        target.parent.mkdir(parents=True, exist_ok=True)
        content = concept.to_markdown()
        target.write_text(content, encoding="utf-8")
        self._append_to_log("create", concept.filepath)
        return target

    def read_concept(self, filepath: str) -> OKFConcept:
        target = self.resolve_path(filepath)
        if not target.exists():
            raise BundleError(f"Concept not found: {filepath}")
        content = target.read_text(encoding="utf-8")
        concept = OKFConcept.from_markdown(filepath, content)

        if not concept.frontmatter.source_hash:
            concept.frontmatter.source_hash = hashlib.sha256(
                content.encode("utf-8")
            ).hexdigest()[:12]

        return concept

    def delete_concept(self, filepath: str):
        target = self.resolve_path(filepath)
        if target.exists():
            target.unlink()
            self._append_to_log("delete", filepath)

    def list_concepts(self, subdir: str = "") -> List[OKFConcept]:
        path = self.workspace_path
        if subdir:
            path = path / subdir
        if not path.is_dir():
            return []
        results = []
        for f in sorted(path.rglob("*.md")):
            if f.name in ("index.md", "log.md"):
                continue
            rel = str(f.relative_to(self.workspace_path)).replace("\\", "/")
            try:
                results.append(self.read_concept(rel))
            except (BundleError, ValueError) as e:
                logger.warning("Skipping unreadable concept %s: %s", rel, e)
        return results

    def export_bundle(self, target_dir: str) -> str:
        export_path = Path(target_dir) / f"{self.workspace_id}-bundle"
        if export_path.exists():
            shutil.rmtree(export_path)
        shutil.copytree(self.workspace_path, export_path)
        self._append_to_log("export", f"bundle exported to {export_path}")
        return str(export_path)

    def hash_content(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]

    def _append_to_log(self, action: str, filepath: str):
        log_path = self.workspace_path / "log.md"
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
        entry = f"| {timestamp} | {action} | {filepath} | system |\n"
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception as e:
            logger.error("Failed to write to audit log %s: %s", log_path, e)

    def validate(self) -> Tuple[bool, List[str], List[str]]:
        result = self.validator.validate_bundle(str(self.workspace_path))
        return result.is_valid, result.errors, result.warnings

    def resolve_links(self, filepath: str) -> List[str]:
        concept = self.read_concept(filepath)
        raw_links = concept.extract_links()
        resolved = []
        for link in raw_links:
            link = link.split("#")[0]
            if link.startswith("http"):
                resolved.append(link)
            else:
                linked_path = os.path.normpath(
                    os.path.join(os.path.dirname(filepath), link)
                ).replace("\\", "/")
                resolved.append(linked_path)
        return resolved
