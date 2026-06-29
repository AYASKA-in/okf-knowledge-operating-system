"""
Seed script: populates a workspace with the sample OKF bundle and syncs metadata to PostgreSQL.
Usage: python seed.py [--workspace-id WS_ID]
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import init_db, get_session_factory
from app.models.db import Workspace, Node, NodeStatus
from app.storage.bundle import BundleManager
from app.config import settings

SAMPLE_BUNDLE_PATH = Path(__file__).parent / "seed_data" / "sample_bundle"


async def seed(workspace_id: str = None):
    await init_db()

    factory = get_session_factory()
    async with factory() as session:
        if workspace_id:
            ws_result = await session.execute(
                __import__("sqlalchemy").select(Workspace).where(Workspace.id == workspace_id)
            )
            ws = ws_result.scalar_one_or_none()
            if not ws:
                print(f"Workspace {workspace_id} not found. Creating...")
                ws = Workspace(
                    id=workspace_id,
                    name=workspace_id,
                    description="Seeded workspace",
                    bucket_path=os.path.join(settings.okf_bundle_root, workspace_id).replace("\\", "/"),
                )
                session.add(ws)
                await session.flush()
        else:
            existing = await session.execute(
                __import__("sqlalchemy").select(Workspace).where(Workspace.name == "sample")
            )
            ws = existing.scalar_one_or_none()
            if ws:
                print(f"Workspace 'sample' already exists (id={ws.id}). Reusing.")
                workspace_id = ws.id
            else:
                import uuid
                workspace_id = str(uuid.uuid4())
                ws = Workspace(
                    id=workspace_id,
                    name="sample",
                    description="Sample enterprise workspace seeded with OKF bundle",
                    bucket_path=os.path.join(settings.okf_bundle_root, workspace_id).replace("\\", "/"),
                )
                session.add(ws)
                await session.flush()
                print(f"Created workspace 'sample' (id={workspace_id})")

        bundle = BundleManager(settings.okf_bundle_root, workspace_id)
        md_files = list(SAMPLE_BUNDLE_PATH.rglob("*.md"))

        count = 0
        for md_path in md_files:
            rel = str(md_path.relative_to(SAMPLE_BUNDLE_PATH)).replace("\\", "/")
            content = md_path.read_text(encoding="utf-8")

            from app.models.okf import OKFConcept
            concept = OKFConcept.from_markdown(rel, content)

            target_path = bundle.workspace_path / rel
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content, encoding="utf-8")

            if md_path.name not in ("index.md", "log.md"):
                body_text = concept.body or ""
                node = Node(
                    workspace_id=workspace_id,
                    concept_path=rel,
                    title=concept.frontmatter.title or md_path.stem,
                    node_type=concept.frontmatter.type,
                    tags=concept.frontmatter.tags or [],
                    status=NodeStatus.published if concept.frontmatter.status == "approved" else NodeStatus.draft,
                    source_hash=bundle.hash_content(content),
                    file_size=len(content.encode("utf-8")),
                    body_text=body_text,
                )
                session.add(node)
                count += 1

        print(f"Seeded {count} concepts into workspace {workspace_id}")
        await session.commit()
        print(f"Bundle path: {bundle.workspace_path}")
        return workspace_id


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed EKOS with sample OKF bundle")
    parser.add_argument("--workspace-id", help="Existing workspace ID to seed into")
    args = parser.parse_args()

    result = asyncio.run(seed(args.workspace_id))
    print(f"Done. Workspace ID: {result}")
