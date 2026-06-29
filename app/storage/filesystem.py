import os
import tempfile
import zipfile
import shutil
from typing import Optional
from pathlib import Path


class FileSystemStore:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def store_raw(self, workspace_id: str, filename: str, content: bytes) -> str:
        dir_path = self.base_path / workspace_id / "raw"
        dir_path.mkdir(parents=True, exist_ok=True)
        target = dir_path / filename
        target.write_bytes(content)
        return str(target)

    def read_raw(self, path: str) -> Optional[bytes]:
        p = Path(path)
        if p.exists():
            return p.read_bytes()
        return None

    def create_zip_archive(self, source_dir: str) -> str:
        source = Path(source_dir)
        if not source.is_dir():
            raise FileNotFoundError(f"Source directory not found: {source_dir}")
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in source.rglob("*"):
                zf.write(file, arcname=file.relative_to(source))
        return tmp.name
