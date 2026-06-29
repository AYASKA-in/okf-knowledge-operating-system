from app.ingestion.connectors.base import DocumentConnector
from app.ingestion.connectors.notion_connector import NotionConnector
from app.ingestion.connectors.git_webhook import GitWebhookConnector
from app.ingestion.connectors.generic_webhook import GenericWebhookConnector


_REGISTRY: dict[str, type[DocumentConnector]] = {
    "notion": NotionConnector,
    "git_webhook": GitWebhookConnector,
    "generic_webhook": GenericWebhookConnector,
}


def get_connector(connector_type: str) -> DocumentConnector:
    cls = _REGISTRY.get(connector_type)
    if not cls:
        raise ValueError(f"Unknown connector type: {connector_type}. Available: {list(_REGISTRY.keys())}")
    return cls()


def list_connector_types() -> list[str]:
    return list(_REGISTRY.keys())
