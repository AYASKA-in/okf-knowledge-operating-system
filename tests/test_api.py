"""API integration tests using SQLite."""
import os
import tempfile
from pathlib import Path
import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.database import Base, get_db
from app.main import app
from app.config import settings
from app.auth.jwt import create_access_token, create_refresh_token
from app.models.db import Workspace, User, Node, NodeStatus, Edge

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="module")
async def test_db():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db

    tmp_bundle = tempfile.mkdtemp(prefix="ekos_test_bundle_")
    original_root = settings.okf_bundle_root
    settings.okf_bundle_root = tmp_bundle

    from app.storage.bundle import BundleManager
    BundleManager(tmp_bundle, "test-ws-1")

    yield factory

    settings.okf_bundle_root = original_root
    import shutil
    shutil.rmtree(tmp_bundle, ignore_errors=True)
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture(scope="module")
async def seed_data(test_db):
    factory = test_db
    async with factory() as session:
        ws = Workspace(id="test-ws-1", name="Test Workspace",
                        description="A test workspace", bucket_path="/tmp/test")
        session.add(ws)
        await session.flush()

        user = User(id="test-user-1", workspace_id="test-ws-1",
                     email="admin@test.com", hashed_password="$2b$12$jTkPEeZEh9Vu35AHNaw4t.pIAorfkA9O.E.CWYbRfjTISiWb0Lf/S",
                     display_name="Admin", role="admin")
        session.add(user)

        viewer = User(id="viewer-user", workspace_id="test-ws-1",
                       email="viewer@test.com", hashed_password="$2b$12$jTkPEeZEh9Vu35AHNaw4t.pIAorfkA9O.E.CWYbRfjTISiWb0Lf/S",
                       display_name="Viewer", role="viewer")
        session.add(viewer)
        await session.commit()

        token = create_access_token(
            user_id="test-user-1",
            workspace_id="test-ws-1",
            role="admin",
        )
        return {"workspace_id": "test-ws-1", "user_id": "test-user-1", "token": token}


class TestAuthEndpoints:
    @pytest.mark.asyncio
    async def test_auth_me_returns_user(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/auth/me", headers={"Authorization": f"Bearer {seed_data['token']}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == "test-user-1"
        assert data["role"] == "admin"

    @pytest.mark.asyncio
    async def test_auth_me_unauthorized(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/auth/me")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_auth_refresh(self, test_db, seed_data):
        token = create_refresh_token(user_id="test-user-1")
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/v1/auth/refresh", json={"refresh_token": token})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    @pytest.mark.asyncio
    async def test_auth_refresh_invalid(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/v1/auth/refresh", json={"refresh_token": "invalid"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_auth_login_invalid_credentials(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/v1/auth/token", json={"email": "admin@test.com", "password": "wrong"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_auth_login_success(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/v1/auth/token", json={"email": "admin@test.com", "password": "admin123"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user_id"] == "test-user-1"
        assert data["workspace_id"] == "test-ws-1"
        assert data["role"] == "admin"


class TestKnowledgeEndpoints:
    @pytest.mark.asyncio
    async def test_list_knowledge_empty(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/knowledge?workspace_id=test-ws-1",
                               headers={"Authorization": f"Bearer {seed_data['token']}"})
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_knowledge_with_total_header(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            await c.post("/v1/knowledge?workspace_id=test-ws-1",
                         headers={"Authorization": f"Bearer {seed_data['token']}"},
                         json={"type": "procedure", "title": "Test"})
            resp = await c.get("/v1/knowledge?workspace_id=test-ws-1",
                               headers={"Authorization": f"Bearer {seed_data['token']}"})
        assert resp.status_code == 200
        assert resp.headers.get("x-total-count") == "1"

    @pytest.mark.asyncio
    async def test_get_concept_not_found(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/knowledge/nonexistent?workspace_id=test-ws-1",
                               headers={"Authorization": f"Bearer {seed_data['token']}"})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_concept_success(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            headers = {"Authorization": f"Bearer {seed_data['token']}"}
            create = await c.post("/v1/knowledge?workspace_id=test-ws-1", headers=headers,
                                  json={"type": "guide", "title": "Getting Started",
                                        "body": "# Getting Started\nWelcome!", "tags": ["docs"]})
            created_id = create.json()["id"]
            resp = await c.get(f"/v1/knowledge/{created_id}?workspace_id=test-ws-1", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == created_id
        assert data["title"] == "Getting Started"
        assert data["type"] == "guide"
        assert data["body"] == "# Getting Started\nWelcome!"
        assert data["tags"] == ["docs"]

    @pytest.mark.asyncio
    async def test_update_concept(self, test_db, seed_data):
        factory = test_db
        async with factory() as session:
            node = Node(id="node-u1", workspace_id="test-ws-1", concept_path="update_test.md",
                         title="Original", node_type="procedure", tags=["test"],
                         status=NodeStatus.draft, body_text="Original body")
            session.add(node)
            await session.commit()

        concept_dir = Path(settings.okf_bundle_root) / "test-ws-1"
        concept_dir.mkdir(parents=True, exist_ok=True)
        (concept_dir / "update_test.md").write_text(
            "---\ntype: procedure\ntitle: Original\n---\n\nOriginal body\n",
            encoding="utf-8"
        )

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.put("/v1/knowledge/node-u1?workspace_id=test-ws-1",
                               headers={"Authorization": f"Bearer {seed_data['token']}"},
                               json={"title": "Updated", "body": "# Updated\nBody."})
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Updated"
        assert data["body"] == "# Updated\nBody."

        async with factory() as session:
            result = await session.execute(select(Node).where(Node.id == "node-u1"))
            n = result.scalar_one()
            assert n.body_text == "# Updated\nBody."

    @pytest.mark.asyncio
    async def test_delete_concept(self, test_db, seed_data):
        factory = test_db
        async with factory() as session:
            node = Node(id="node-del", workspace_id="test-ws-1", concept_path="del.md",
                         title="Delete Me", node_type="faq", tags=[],
                         status=NodeStatus.draft, body_text="")
            session.add(node)
            await session.commit()

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.delete("/v1/knowledge/node-del?workspace_id=test-ws-1",
                                  headers={"Authorization": f"Bearer {seed_data['token']}"})
            assert resp.status_code == 200

            resp = await c.get("/v1/knowledge/node-del?workspace_id=test-ws-1",
                               headers={"Authorization": f"Bearer {seed_data['token']}"})
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_concept(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/v1/knowledge?workspace_id=test-ws-1",
                                headers={"Authorization": f"Bearer {seed_data['token']}"},
                                json={"type": "procedure", "title": "New Concept",
                                      "body": "# New\nBody.", "tags": ["test"]})
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "New Concept"
        assert data["type"] == "procedure"
        assert data["body"] == "# New\nBody."
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_concept_duplicate_path(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            await c.post("/v1/knowledge?workspace_id=test-ws-1",
                         headers={"Authorization": f"Bearer {seed_data['token']}"},
                         json={"type": "faq", "title": "Duplicate"})
            resp = await c.post("/v1/knowledge?workspace_id=test-ws-1",
                                headers={"Authorization": f"Bearer {seed_data['token']}"},
                                json={"type": "faq", "title": "Duplicate"})
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_create_concept_unauthorized(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/v1/knowledge?workspace_id=test-ws-1",
                                headers={},
                                json={"type": "procedure", "title": "No Auth"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_create_concept_creates_edges(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            headers = {"Authorization": f"Bearer {seed_data['token']}"}
            await c.post("/v1/knowledge?workspace_id=test-ws-1", headers=headers,
                          json={"type": "policy", "title": "Acme Protocol",
                                "body": "Acme protocol must be followed."})
            resp = await c.post("/v1/knowledge?workspace_id=test-ws-1", headers=headers,
                                json={"type": "guide", "title": "Acme Guide",
                                      "body": "Guide to Acme protocol."})
        assert resp.status_code == 201
        data = resp.json()
        assert "## See Also" in data["body"]

        factory = test_db
        async with factory() as session:
            edges = await session.execute(
                select(Edge).where(Edge.workspace_id == "test-ws-1")
            )
            edge_list = edges.scalars().all()
        assert len(edge_list) >= 1

    @pytest.mark.asyncio
    async def test_get_concept_links(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            headers = {"Authorization": f"Bearer {seed_data['token']}"}
            create = await c.post("/v1/knowledge?workspace_id=test-ws-1", headers=headers,
                                  json={"type": "note", "title": "Linked Page"})
            created_id = create.json()["id"]
            resp = await c.post(f"/v1/knowledge/{created_id}/links?workspace_id=test-ws-1", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["filepath"] == create.json()["filepath"]
        assert "markdown_links" in data
        assert "edges" in data

    @pytest.mark.asyncio
    async def test_get_concept_links_not_found(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/v1/knowledge/nonexistent/links?workspace_id=test-ws-1",
                               headers={"Authorization": f"Bearer {seed_data['token']}"})
        assert resp.status_code == 404


class TestSearchEndpoints:
    @pytest.mark.asyncio
    async def test_search_empty(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/v1/search",
                                headers={"Authorization": f"Bearer {seed_data['token']}"},
                                json={"workspace_id": "test-ws-1", "query": "nonexistent"})
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_search_finds_content(self, test_db, seed_data):
        factory = test_db
        async with factory() as session:
            node = Node(id="search-n", workspace_id="test-ws-1", concept_path="security.md",
                         title="Security Policy", node_type="policy",
                         tags=["security"], status=NodeStatus.draft,
                         body_text="All employees must follow security guidelines.")
            session.add(node)
            await session.commit()

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/v1/search",
                                headers={"Authorization": f"Bearer {seed_data['token']}"},
                                json={"workspace_id": "test-ws-1", "query": "security"})
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    @pytest.mark.asyncio
    async def test_search_with_total_header(self, test_db, seed_data):
        factory = test_db
        async with factory() as session:
            session.add(Node(id="search-th1", workspace_id="test-ws-1", concept_path="th1.md",
                              title="TH1", node_type="policy", tags=[], status=NodeStatus.draft,
                              body_text="alpha beta gamma"))
            session.add(Node(id="search-th2", workspace_id="test-ws-1", concept_path="th2.md",
                              title="TH2", node_type="policy", tags=[], status=NodeStatus.draft,
                              body_text="delta beta epsilon"))
            await session.commit()

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/v1/search",
                                headers={"Authorization": f"Bearer {seed_data['token']}"},
                                json={"workspace_id": "test-ws-1", "query": "beta"})
        assert resp.status_code == 200
        assert resp.headers.get("x-total-count") == "2"

    @pytest.mark.asyncio
    async def test_search_with_type_filter(self, test_db, seed_data):
        factory = test_db
        async with factory() as session:
            session.add(Node(id="search-tf1", workspace_id="test-ws-1", concept_path="tf1.md",
                              title="TF1", node_type="policy", tags=[], status=NodeStatus.draft,
                              body_text="unique term xyz"))
            session.add(Node(id="search-tf2", workspace_id="test-ws-1", concept_path="tf2.md",
                              title="TF2", node_type="guide", tags=[], status=NodeStatus.draft,
                              body_text="unique term xyz"))
            await session.commit()

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/v1/search",
                                headers={"Authorization": f"Bearer {seed_data['token']}"},
                                json={"workspace_id": "test-ws-1", "query": "unique",
                                      "type_filter": "policy"})
        assert resp.status_code == 200
        results = resp.json()
        assert all(r["type"] == "policy" for r in results)
        assert results[0]["title"] == "TF1"

    @pytest.mark.asyncio
    async def test_search_with_tag(self, test_db, seed_data):
        factory = test_db
        async with factory() as session:
            session.add(Node(id="search-tag1", workspace_id="test-ws-1", concept_path="tag1.md",
                              title="Tagged One", node_type="note", tags=["important", "urgent"],
                              status=NodeStatus.draft, body_text="tagged content here"))
            session.add(Node(id="search-tag2", workspace_id="test-ws-1", concept_path="tag2.md",
                              title="Tagged Two", node_type="note", tags=["important"],
                              status=NodeStatus.draft, body_text="more tagged content"))
            await session.commit()

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/v1/search",
                                headers={"Authorization": f"Bearer {seed_data['token']}"},
                                json={"workspace_id": "test-ws-1", "query": "tagged",
                                      "tag": "urgent"})
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) == 1
        assert results[0]["title"] == "Tagged One"

    @pytest.mark.asyncio
    async def test_search_edge_boost(self, test_db, seed_data):
        factory = test_db
        async with factory() as session:
            session.add(Node(id="boost-a", workspace_id="test-ws-1", concept_path="boost_a.md",
                              title="Boost A", node_type="note", tags=[], status=NodeStatus.draft,
                              body_text="unique phrase echo"))
            session.add(Node(id="boost-b", workspace_id="test-ws-1", concept_path="boost_b.md",
                              title="Boost B", node_type="note", tags=[], status=NodeStatus.draft,
                              body_text="unique phrase echo"))
            for i in range(3):
                session.add(Node(id=f"src-a{i}", workspace_id="test-ws-1", concept_path=f"src_a{i}.md",
                                  title=f"Source A{i}", node_type="note", tags=[], status=NodeStatus.draft,
                                  body_text="source"))
            session.add(Node(id="src-b", workspace_id="test-ws-1", concept_path="src_b.md",
                              title="Source B", node_type="note", tags=[], status=NodeStatus.draft,
                              body_text="source"))
            await session.commit()

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            headers = {"Authorization": f"Bearer {seed_data['token']}"}
            for i in range(3):
                await c.post("/v1/edges", headers=headers,
                              json={"workspace_id": "test-ws-1", "source_id": f"src-a{i}",
                                    "target_id": "boost-a", "edge_type": "references"})
            await c.post("/v1/edges", headers=headers,
                          json={"workspace_id": "test-ws-1", "source_id": "src-b",
                                "target_id": "boost-b", "edge_type": "references"})

            resp = await c.post("/v1/search", headers=headers,
                                json={"workspace_id": "test-ws-1", "query": "unique phrase"})
        assert resp.status_code == 200
        results = resp.json()
        a_score = next(r["score"] for r in results if r["id"] == "boost-a")
        b_score = next(r["score"] for r in results if r["id"] == "boost-b")
        assert a_score > b_score


class TestAdminEndpoints:
    @pytest.mark.asyncio
    async def test_list_workspaces(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/admin/workspaces",
                               headers={"Authorization": f"Bearer {seed_data['token']}"})
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    @pytest.mark.asyncio
    async def test_create_user(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/v1/admin/users",
                                headers={"Authorization": f"Bearer {seed_data['token']}"},
                                json={"workspace_id": "test-ws-1", "email": "new@test.com",
                                       "password": "pass123", "display_name": "New", "role": "viewer"})
        assert resp.status_code == 201
        assert resp.json()["email"] == "new@test.com"

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            headers = {"Authorization": f"Bearer {seed_data['token']}"}
            await c.post("/v1/admin/users", headers=headers,
                          json={"workspace_id": "test-ws-1", "email": "dup@test.com",
                                "password": "p1", "display_name": "D1", "role": "viewer"})
            resp = await c.post("/v1/admin/users", headers=headers,
                                json={"workspace_id": "test-ws-1", "email": "dup@test.com",
                                      "password": "p2", "display_name": "D2", "role": "editor"})
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.put("/v1/admin/users/nonexistent",
                                headers={"Authorization": f"Bearer {seed_data['token']}"},
                                json={"display_name": "Ghost"})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_user_workspace_not_found(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/v1/admin/users",
                                headers={"Authorization": f"Bearer {seed_data['token']}"},
                                json={"workspace_id": "nonexistent", "email": "nope@test.com",
                                      "password": "p", "display_name": "Nope", "role": "viewer"})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_viewer_cannot_create_user(self, test_db, seed_data):
        token = create_access_token(user_id="viewer-user", workspace_id="test-ws-1", role="viewer")
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/v1/admin/users",
                                headers={"Authorization": f"Bearer {token}"},
                                json={"workspace_id": "test-ws-1", "email": "v@test.com",
                                       "password": "p", "display_name": "V", "role": "admin"})
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_audit_logs(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/admin/audit-logs?workspace_id=test-ws-1",
                               headers={"Authorization": f"Bearer {seed_data['token']}"})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_create_workspace(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/v1/admin/workspaces",
                                headers={"Authorization": f"Bearer {seed_data['token']}"},
                                json={"name": "New-WS", "description": "Brand new"})
        assert resp.status_code == 201
        assert resp.json()["name"] == "New-WS"

    @pytest.mark.asyncio
    async def test_create_workspace_duplicate(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/v1/admin/workspaces",
                                headers={"Authorization": f"Bearer {seed_data['token']}"},
                                json={"name": "Test Workspace"})
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_get_workspace(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            headers = {"Authorization": f"Bearer {seed_data['token']}"}
            list_resp = await c.get("/v1/admin/workspaces", headers=headers)
            test_ws = next(ws for ws in list_resp.json() if ws["name"] == "Test Workspace")
            resp = await c.get(f"/v1/admin/workspaces/{test_ws['id']}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Test Workspace"

    @pytest.mark.asyncio
    async def test_get_workspace_not_found(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/admin/workspaces/nonexistent",
                               headers={"Authorization": f"Bearer {seed_data['token']}"})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_workspace(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            headers = {"Authorization": f"Bearer {seed_data['token']}"}
            list_resp = await c.get("/v1/admin/workspaces", headers=headers)
            test_ws = next(ws for ws in list_resp.json() if ws["name"] == "Test Workspace")
            resp = await c.put(f"/v1/admin/workspaces/{test_ws['id']}", headers=headers,
                               json={"description": "Updated description"})
        assert resp.status_code == 200
        assert resp.json()["description"] == "Updated description"

    @pytest.mark.asyncio
    async def test_update_workspace_duplicate_name(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            headers = {"Authorization": f"Bearer {seed_data['token']}"}
            await c.post("/v1/admin/workspaces", headers=headers,
                         json={"name": "Unique-WS", "description": ""})
            ws_list = await c.get("/v1/admin/workspaces", headers=headers)
            test_ws = next(ws for ws in ws_list.json() if ws["name"] == "Test Workspace")
            resp = await c.put(f"/v1/admin/workspaces/{test_ws['id']}", headers=headers,
                               json={"name": "Unique-WS"})
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_list_users(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/admin/users",
                               headers={"Authorization": f"Bearer {seed_data['token']}"})
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    @pytest.mark.asyncio
    async def test_list_users_filter_by_workspace(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/admin/users?workspace_id=test-ws-1",
                               headers={"Authorization": f"Bearer {seed_data['token']}"})
        assert resp.status_code == 200
        assert all(u["workspace_id"] == "test-ws-1" for u in resp.json())

    @pytest.mark.asyncio
    async def test_get_user(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            headers = {"Authorization": f"Bearer {seed_data['token']}"}
            users = await c.get("/v1/admin/users", headers=headers)
            user_id = users.json()[0]["id"]
            resp = await c.get(f"/v1/admin/users/{user_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == user_id

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/admin/users/nonexistent",
                               headers={"Authorization": f"Bearer {seed_data['token']}"})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_user(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            headers = {"Authorization": f"Bearer {seed_data['token']}"}
            resp = await c.put(f"/v1/admin/users/{seed_data['user_id']}", headers=headers,
                               json={"display_name": "Updated Name"})
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_deactivate_and_restore_user(self, test_db, seed_data):
        factory = test_db
        async with factory() as session:
            from app.auth.password import hash_password
            tmp = User(id="user-toggle", workspace_id="test-ws-1",
                        email="toggle@test.com", hashed_password=hash_password("p"),
                        display_name="Toggle", role="viewer")
            session.add(tmp)
            await session.commit()

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            headers = {"Authorization": f"Bearer {seed_data['token']}"}
            deact = await c.put("/v1/admin/users/user-toggle", headers=headers,
                                json={"is_active": False})
            assert deact.json()["is_active"] is False
            act = await c.put("/v1/admin/users/user-toggle", headers=headers,
                              json={"is_active": True})
            assert act.json()["is_active"] is True

    @pytest.mark.asyncio
    async def test_update_user_duplicate_email(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            headers = {"Authorization": f"Bearer {seed_data['token']}"}
            users = await c.get("/v1/admin/users", headers=headers)
            first, second = users.json()[0], users.json()[1]
            resp = await c.put(f"/v1/admin/users/{second['id']}", headers=headers,
                               json={"email": first["email"]})
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_delete_user(self, test_db, seed_data):
        factory = test_db
        async with factory() as session:
            from app.auth.password import hash_password
            tmp = User(id="user-to-delete", workspace_id="test-ws-1",
                        email="delete@test.com", hashed_password=hash_password("p"),
                        display_name="Delete Me", role="viewer")
            session.add(tmp)
            await session.commit()

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            headers = {"Authorization": f"Bearer {seed_data['token']}"}
            resp = await c.delete("/v1/admin/users/user-to-delete", headers=headers)
            assert resp.status_code == 200
            get_resp = await c.get("/v1/admin/users/user-to-delete", headers=headers)
            assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.delete("/v1/admin/users/nonexistent",
                                  headers={"Authorization": f"Bearer {seed_data['token']}"})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_workspace(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            headers = {"Authorization": f"Bearer {seed_data['token']}"}
            create = await c.post("/v1/admin/workspaces", headers=headers,
                                  json={"name": "To-Delete", "description": ""})
            ws_id = create.json()["id"]
            resp = await c.delete(f"/v1/admin/workspaces/{ws_id}", headers=headers)
            assert resp.status_code == 200
            get_resp = await c.get(f"/v1/admin/workspaces/{ws_id}", headers=headers)
            assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_workspace_not_found(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.delete("/v1/admin/workspaces/nonexistent",
                                  headers={"Authorization": f"Bearer {seed_data['token']}"})
        assert resp.status_code == 404


class TestIngestEndpoint:
    @pytest.mark.asyncio
    async def test_ingest_document(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/v1/ingest",
                                headers={"Authorization": f"Bearer {seed_data['token']}"},
                                json={"workspace_id": "test-ws-1", "filename": "test.md",
                                       "content": "# Intro\n\nText.\n\n# Details\n\nMore.",
                                       "source_type": "markdown"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestChatEndpoint:
    @pytest.mark.asyncio
    async def test_chat_no_context(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/v1/chat",
                                headers={"Authorization": f"Bearer {seed_data['token']}"},
                                json={"workspace_id": "test-ws-1", "message": "Unknown topic"})
        assert resp.status_code == 200
        assert "cannot answer" in resp.json()["answer"].lower()

    @pytest.mark.asyncio
    async def test_chat_with_citations(self, test_db, seed_data):
        from app.storage.bundle import BundleManager
        from app.models.okf import OKFConcept, OKFFrontmatter
        bundle = BundleManager(settings.okf_bundle_root, "test-ws-1")
        concept = OKFConcept(
            filepath="onboarding.md",
            frontmatter=OKFFrontmatter(type="guide", title="Onboarding Guide"),
            body="# Onboarding\n\nNew hires must complete the security training within 7 days.\n",
        )
        bundle.write_concept(concept)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/v1/chat",
                                headers={"Authorization": f"Bearer {seed_data['token']}"},
                                json={"workspace_id": "test-ws-1", "message": "What about security training?"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["citations"]) > 0
        assert "security" in data["answer"].lower()
        assert data["citations"][0]["filepath"] == "onboarding.md"


class TestExportEndpoint:
    @pytest.mark.asyncio
    async def test_export(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/v1/export",
                                headers={"Authorization": f"Bearer {seed_data['token']}"},
                                json={"workspace_id": "test-ws-1"})
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"

    @pytest.mark.asyncio
    async def test_export_with_concepts(self, test_db, seed_data):
        from app.storage.bundle import BundleManager
        from app.models.okf import OKFConcept, OKFFrontmatter
        bundle = BundleManager(settings.okf_bundle_root, "test-ws-1")
        concept = OKFConcept(
            filepath="export_test.md",
            frontmatter=OKFFrontmatter(type="note", title="Test Export"),
            body="# Test\n\nContent for export.\n",
        )
        bundle.write_concept(concept)
        assert (bundle.workspace_path / "export_test.md").exists()

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/v1/export",
                                headers={"Authorization": f"Bearer {seed_data['token']}"},
                                json={"workspace_id": "test-ws-1"})
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"
        import zipfile
        import io
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            names = zf.namelist()
            assert any("export_test.md" in n for n in names)


class TestEdgeEndpoints:
    @pytest.mark.asyncio
    async def test_create_edge(self, test_db, seed_data):
        factory = test_db
        async with factory() as session:
            src = Node(id="edge-src", workspace_id="test-ws-1", concept_path="src.md",
                        title="Source", node_type="concept", tags=[], status=NodeStatus.draft)
            tgt = Node(id="edge-tgt", workspace_id="test-ws-1", concept_path="tgt.md",
                        title="Target", node_type="concept", tags=[], status=NodeStatus.draft)
            session.add_all([src, tgt])
            await session.commit()

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/v1/edges",
                                headers={"Authorization": f"Bearer {seed_data['token']}"},
                                json={"workspace_id": "test-ws-1", "source_id": "edge-src",
                                      "target_id": "edge-tgt", "edge_type": "references"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["source_id"] == "edge-src"
        assert data["target_id"] == "edge-tgt"
        assert data["edge_type"] == "references"

    @pytest.mark.asyncio
    async def test_create_edge_duplicate(self, test_db, seed_data):
        factory = test_db
        async with factory() as session:
            src = Node(id="edge-src2", workspace_id="test-ws-1", concept_path="src2.md",
                        title="S2", node_type="concept", tags=[], status=NodeStatus.draft)
            tgt = Node(id="edge-tgt2", workspace_id="test-ws-1", concept_path="tgt2.md",
                        title="T2", node_type="concept", tags=[], status=NodeStatus.draft)
            session.add_all([src, tgt])
            await session.commit()

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            payload = {"workspace_id": "test-ws-1", "source_id": "edge-src2",
                       "target_id": "edge-tgt2", "edge_type": "depends_on"}
            await c.post("/v1/edges", headers={"Authorization": f"Bearer {seed_data['token']}"}, json=payload)
            resp = await c.post("/v1/edges", headers={"Authorization": f"Bearer {seed_data['token']}"}, json=payload)
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_create_edge_invalid_type(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/v1/edges",
                                headers={"Authorization": f"Bearer {seed_data['token']}"},
                                json={"workspace_id": "test-ws-1", "source_id": "x",
                                      "target_id": "y", "edge_type": "invalid"})
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_list_concept_edges(self, test_db, seed_data):
        factory = test_db
        async with factory() as session:
            src = Node(id="edge-src3", workspace_id="test-ws-1", concept_path="src3.md",
                        title="S3", node_type="concept", tags=[], status=NodeStatus.draft)
            tgt = Node(id="edge-tgt3", workspace_id="test-ws-1", concept_path="tgt3.md",
                        title="T3", node_type="concept", tags=[], status=NodeStatus.draft)
            session.add_all([src, tgt])
            await session.commit()

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            headers = {"Authorization": f"Bearer {seed_data['token']}"}
            await c.post("/v1/edges", headers=headers,
                         json={"workspace_id": "test-ws-1", "source_id": "edge-src3",
                               "target_id": "edge-tgt3", "edge_type": "related_to"})
            resp = await c.get("/v1/knowledge/edge-src3/edges?workspace_id=test-ws-1", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["edge_type"] == "related_to"

    @pytest.mark.asyncio
    async def test_list_concept_edges_not_found(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/knowledge/nonexistent/edges?workspace_id=test-ws-1",
                               headers={"Authorization": f"Bearer {seed_data['token']}"})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_edge(self, test_db, seed_data):
        factory = test_db
        async with factory() as session:
            src = Node(id="edge-src4", workspace_id="test-ws-1", concept_path="src4.md",
                        title="S4", node_type="concept", tags=[], status=NodeStatus.draft)
            tgt = Node(id="edge-tgt4", workspace_id="test-ws-1", concept_path="tgt4.md",
                        title="T4", node_type="concept", tags=[], status=NodeStatus.draft)
            session.add_all([src, tgt])
            await session.commit()

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            headers = {"Authorization": f"Bearer {seed_data['token']}"}
            create = await c.post("/v1/edges", headers=headers,
                                  json={"workspace_id": "test-ws-1", "source_id": "edge-src4",
                                        "target_id": "edge-tgt4", "edge_type": "references"})
            edge_id = create.json()["id"]
            del_resp = await c.delete(f"/v1/edges/{edge_id}", headers=headers)
        assert del_resp.status_code == 200
        assert del_resp.json()["deleted"] == edge_id

    @pytest.mark.asyncio
    async def test_delete_edge_not_found(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.delete("/v1/edges/nonexistent",
                                  headers={"Authorization": f"Bearer {seed_data['token']}"})
        assert resp.status_code == 404


class TestGraphEndpoints:
    @pytest.mark.asyncio
    async def test_subgraph_basic(self, test_db, seed_data):
        factory = test_db
        async with factory() as session:
            a = Node(id="graph-a", workspace_id="test-ws-1", concept_path="a.md",
                      title="Node A", node_type="concept", tags=[], status=NodeStatus.draft)
            b = Node(id="graph-b", workspace_id="test-ws-1", concept_path="b.md",
                      title="Node B", node_type="concept", tags=[], status=NodeStatus.draft)
            c = Node(id="graph-c", workspace_id="test-ws-1", concept_path="c.md",
                      title="Node C", node_type="concept", tags=[], status=NodeStatus.draft)
            session.add_all([a, b, c])
            e1 = Edge(id="ge1", workspace_id="test-ws-1", source_id="graph-a", target_id="graph-b", edge_type="references")
            e2 = Edge(id="ge2", workspace_id="test-ws-1", source_id="graph-b", target_id="graph-c", edge_type="depends_on")
            session.add_all([e1, e2])
            await session.commit()

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            headers = {"Authorization": f"Bearer {seed_data['token']}"}
            resp = await c.get("/v1/knowledge/graph-a/graph?workspace_id=test-ws-1&depth=1", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1
        assert data["edges"][0]["type"] == "references"

    @pytest.mark.asyncio
    async def test_subgraph_depth2(self, test_db, seed_data):
        factory = test_db
        async with factory() as session:
            a = Node(id="gd2-a", workspace_id="test-ws-1", concept_path="d2_a.md",
                      title="A", node_type="concept", tags=[], status=NodeStatus.draft)
            b = Node(id="gd2-b", workspace_id="test-ws-1", concept_path="d2_b.md",
                      title="B", node_type="concept", tags=[], status=NodeStatus.draft)
            c = Node(id="gd2-c", workspace_id="test-ws-1", concept_path="d2_c.md",
                      title="C", node_type="concept", tags=[], status=NodeStatus.draft)
            session.add_all([a, b, c])
            session.add_all([
                Edge(id="ge2a", workspace_id="test-ws-1", source_id="gd2-a", target_id="gd2-b", edge_type="references"),
                Edge(id="ge2b", workspace_id="test-ws-1", source_id="gd2-b", target_id="gd2-c", edge_type="related_to"),
            ])
            await session.commit()

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            headers = {"Authorization": f"Bearer {seed_data['token']}"}
            resp = await c.get("/v1/knowledge/gd2-a/graph?workspace_id=test-ws-1&depth=2", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["nodes"]) == 3
        assert len(data["edges"]) == 2

    @pytest.mark.asyncio
    async def test_subgraph_not_found(self, test_db, seed_data):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/knowledge/nonexistent/graph?workspace_id=test-ws-1",
                               headers={"Authorization": f"Bearer {seed_data['token']}"})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_graph_path(self, test_db, seed_data):
        factory = test_db
        async with factory() as session:
            a = Node(id="gp-a", workspace_id="test-ws-1", concept_path="gp_a.md",
                      title="Alpha", node_type="concept", tags=[], status=NodeStatus.draft)
            b = Node(id="gp-b", workspace_id="test-ws-1", concept_path="gp_b.md",
                      title="Beta", node_type="concept", tags=[], status=NodeStatus.draft)
            c = Node(id="gp-c", workspace_id="test-ws-1", concept_path="gp_c.md",
                      title="Gamma", node_type="concept", tags=[], status=NodeStatus.draft)
            session.add_all([a, b, c])
            session.add_all([
                Edge(id="gpea", workspace_id="test-ws-1", source_id="gp-a", target_id="gp-b", edge_type="references"),
                Edge(id="gpeb", workspace_id="test-ws-1", source_id="gp-b", target_id="gp-c", edge_type="depends_on"),
            ])
            await session.commit()

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/v1/graph/path",
                                headers={"Authorization": f"Bearer {seed_data['token']}"},
                                json={"workspace_id": "test-ws-1", "source_id": "gp-a", "target_id": "gp-c"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["path_found"] is True
        assert len(data["nodes"]) == 3
        assert len(data["edges"]) == 2
        assert data["edges"][0]["source"] == "gp-a"

    @pytest.mark.asyncio
    async def test_graph_path_not_found(self, test_db, seed_data):
        factory = test_db
        async with factory() as session:
            a = Node(id="gpn-a", workspace_id="test-ws-1", concept_path="gpn_a.md",
                      title="A", node_type="concept", tags=[], status=NodeStatus.draft)
            b = Node(id="gpn-b", workspace_id="test-ws-1", concept_path="gpn_b.md",
                      title="B", node_type="concept", tags=[], status=NodeStatus.draft)
            session.add_all([a, b])
            await session.commit()

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/v1/graph/path",
                                headers={"Authorization": f"Bearer {seed_data['token']}"},
                                json={"workspace_id": "test-ws-1", "source_id": "gpn-a", "target_id": "gpn-b"})
        assert resp.status_code == 200
        assert resp.json()["path_found"] is False
