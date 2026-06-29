import httpx
from app.ingestion.models import ParsedDocument, Section
from app.ingestion.connectors.base import DocumentConnector


class GitWebhookConnector(DocumentConnector):
    connector_type = "git_webhook"

    async def fetch(self, config: dict) -> list[ParsedDocument]:
        raise RuntimeError("GitWebhookConnector does not support fetch; use process_push instead")

    async def validate_config(self, config: dict) -> str:
        token = config.get("token", "")
        repo = config.get("repo", "")
        if not token:
            return "Missing GitHub token"
        if not repo:
            return "Missing repo (format: owner/name)"
        try:
            async with httpx.AsyncClient() as c:
                resp = await c.get(
                    f"https://api.github.com/repos/{repo}",
                    headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"},
                )
                if resp.status_code == 200:
                    return "ok"
                return f"GitHub API error: {resp.status_code}"
        except Exception as e:
            return f"Connection error: {e}"

    async def process_push(self, config: dict, payload: dict) -> list[ParsedDocument]:
        token = config.get("token", "")
        repo = payload.get("repository", {}).get("full_name", "")
        default_branch = payload.get("ref", "").replace("refs/heads/", "")

        docs: list[ParsedDocument] = []
        seen_paths: set[str] = set()

        for commit in payload.get("commits", []):
            for filename in commit.get("added", []) + commit.get("modified", []):
                if not filename.endswith(".md"):
                    continue
                if filename in seen_paths:
                    continue
                seen_paths.add(filename)

                content = await self._fetch_file(repo, filename, token, default_branch)
                if content is not None:
                    docs.append(ParsedDocument(
                        title=filename.replace(".md", "").replace("/", "_"),
                        sections=[Section(title=filename, text=content)],
                        source_type="markdown",
                        metadata={
                            "repo": repo,
                            "filepath": filename,
                            "commit": commit.get("id", ""),
                            "branch": default_branch,
                        },
                    ))

        return docs

    async def _fetch_file(self, repo: str, path: str, token: str, branch: str) -> str | None:
        url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={branch}"
        async with httpx.AsyncClient() as c:
            resp = await c.get(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3.raw",
                },
            )
            if resp.status_code == 200:
                return resp.text
        return None
