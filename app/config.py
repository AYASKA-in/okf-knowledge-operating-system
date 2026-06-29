from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://ekos:ekos@localhost:5432/ekos"
    database_url_sync: str = "postgresql+psycopg2://ekos:ekos@localhost:5432/ekos"

    gcp_project_id: str = ""
    gcp_location: str = "us-central1"
    vertex_ai_location: str = "us-central1"
    google_application_credentials: str = ""

    okf_bundle_root: str = "./data/bundles"
    okf_default_workspace: str = "default"

    jwt_secret: str = "change-this-to-a-secure-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24
    jwt_refresh_expiry_days: int = 7

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: List[str] = ["http://localhost:3000"]

    ingestion_model: str = "gemini-1.5-flash-002"
    chat_model: str = "gemini-1.5-pro-002"
    embedding_model: str = "text-embedding-004"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

os.makedirs(settings.okf_bundle_root, exist_ok=True)
