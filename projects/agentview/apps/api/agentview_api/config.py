from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class AppConfig:
    missing_categories: list[str]
    database_path: str
    environment: str
    public_url: str
    api_url: str
    database_mode: str
    bootstrap_threshold: int
    max_upload_bytes: int


def _path(value: str | None, default: str) -> str:
    return value or default


def load_config() -> AppConfig:
    categories = [
        ("model provider", "OPENAI_API_KEY"),
        ("YouTube public API key", "YOUTUBE_API_KEY"),
        ("Google OAuth client", "GOOGLE_OAUTH_CLIENT_ID"),
        ("signing provider", "SIGNING_PROVIDER"),
        ("object storage", "S3_ENDPOINT_URL"),
        ("OIDC issuer", "OIDC_ISSUER"),
    ]
    missing = [label for label, envvar in categories if not os.getenv(envvar)]
    return AppConfig(
        missing_categories=missing,
        database_path=_path(os.getenv("AGENTVIEW_DATABASE_PATH"), str(Path.home() / ".agentview.sqlite3")),
        environment=_path(os.getenv("AGENTVIEW_ENV"), "development"),
        public_url=_path(os.getenv("AGENTVIEW_PUBLIC_URL"), "http://localhost:8000"),
        api_url=_path(os.getenv("AGENTVIEW_API_URL"), "http://localhost:8000"),
        database_mode=_path(os.getenv("AGENTVIEW_DATABASE_MODE"), "sqlite"),
        bootstrap_threshold=int(os.getenv("AGENTVIEW_BOOTSTRAP_THRESHOLD", "1000")),
        max_upload_bytes=int(os.getenv("AGENTVIEW_MAX_UPLOAD_BYTES", str(250 * 1024 * 1024))),
    )
