import hashlib
import hmac
from typing import Optional
from app.ingestion.models import ParsedDocument, Section
from app.ingestion.connectors.base import DocumentConnector


SECRET_PREFIX = "sh-webhook-"


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


class GenericWebhookConnector(DocumentConnector):
    connector_type = "generic_webhook"

    async def fetch(self, config: dict) -> list[ParsedDocument]:
        raise RuntimeError("GenericWebhookConnector does not support fetch; use process_payload instead")

    async def validate_config(self, config: dict) -> str:
        secret = config.get("secret", "")
        if not secret:
            return "Missing secret"
        if not secret.startswith(SECRET_PREFIX):
            return "Secret must start with " + SECRET_PREFIX
        return "ok"

    async def process_payload(self, config: dict, payload: dict, raw_bytes: bytes, signature: str) -> list[ParsedDocument]:
        secret = config.get("secret", "")
        if secret:
            if not verify_signature(raw_bytes, signature, secret):
                raise ValueError("HMAC signature mismatch")

        docs: list[ParsedDocument] = []
        entries = payload if isinstance(payload, list) else [payload]
        for entry in entries:
            title = entry.get("title", entry.get("name", "webhook_ingest"))
            content = entry.get("content", entry.get("body", entry.get("text", "")))
            sections_text = entry.get("sections", [])
            source_type = entry.get("source_type", "webhook")

            if sections_text:
                sections = [Section(title=s.get("title", "section"), text=s.get("text", "")) for s in sections_text]
            else:
                sections = [Section(title=title, text=content)]

            docs.append(ParsedDocument(
                title=title,
                sections=[s for s in sections if s.text],
                source_type=source_type,
                metadata=entry.get("metadata", {}),
            ))

        return docs
