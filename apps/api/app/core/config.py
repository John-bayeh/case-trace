"""Shared settings for API, migrations and future maintenance commands."""

import os
from pathlib import Path
from typing import Literal, TypedDict, Unpack

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url


def default_root() -> Path:
    override = os.environ.get("CASETRACE_ROOT")
    if override:
        root = Path(override)
    else:
        root = Path(__file__).resolve().parents[4]
    if not root.is_absolute() or not (root / "apps" / "api").is_dir():
        raise ValueError("CASETRACE_ROOT must be an absolute root containing apps/api")
    return root


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False)

    casetrace_root: Path = Field(default_factory=default_root)
    app_env: Literal["development", "test", "production"] = "development"
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)
    database_url: str = "sqlite+aiosqlite:///./data/runtime/casetrace.db"
    sqlite_busy_timeout_ms: int = Field(default=5000, ge=0, le=60000)
    asset_storage_path: Path = Path("data/assets")
    cors_allowed_origins: list[str] = ["http://localhost:3000"]
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    llm_provider: Literal["rules", "gemini", "openai"] = "rules"
    llm_model: str = Field(default="", pattern=r"^[A-Za-z0-9._-]*$")
    llm_api_key: str = Field(default="", repr=False)
    openai_api_key: str = Field(default="", repr=False)
    openai_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = Field(default=30, gt=0, le=120)
    llm_max_retries: int = Field(default=1, ge=0, le=2)
    llm_max_output_tokens: int = Field(default=4000, ge=100, le=16000)
    investigation_timeout_seconds: float = Field(default=180, gt=0, le=600)
    investigation_max_tool_calls: int = Field(default=100, ge=1, le=300)
    investigation_max_calls_per_agent: int = Field(default=30, ge=1, le=100)
    investigation_max_context_chars: int = Field(default=100000, ge=1000, le=500000)
    investigation_strategy: Literal["baseline", "adaptive_rules"] = "baseline"
    investigation_reasoning: Literal["legacy", "structured"] = "legacy"
    investigation_max_tasks: int = Field(default=40, ge=1, le=100)
    investigation_max_depth: int = Field(default=2, ge=0, le=5)
    investigation_max_followup_iterations: int = Field(default=2, ge=0, le=5)
    investigation_max_concurrency: int = Field(default=2, ge=1, le=4)
    investigation_task_attempts: int = Field(default=1, ge=1, le=3)
    investigation_max_candidates: int = Field(default=40, ge=1, le=100)
    investigation_max_leads: int = Field(default=40, ge=1, le=100)

    @field_validator("casetrace_root")
    @classmethod
    def validate_root(cls, value: Path) -> Path:
        if not value.is_absolute() or not (value / "apps" / "api").is_dir():
            raise ValueError("CASETRACE_ROOT must be an absolute root containing apps/api")
        return value.resolve()

    @field_validator("database_url")
    @classmethod
    def validate_database(cls, value: str) -> str:
        url = make_url(value)
        if (
            url.drivername != "sqlite+aiosqlite"
            or not url.database
            or url.host
            or url.username
            or url.password
            or url.query
        ):
            raise ValueError("Use a plain sqlite+aiosqlite file URL or :memory:")
        return value

    @field_validator("cors_allowed_origins")
    @classmethod
    def validate_origins(cls, values: list[str]) -> list[str]:
        from urllib.parse import urlsplit

        for value in values:
            parsed = urlsplit(value)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.username
            ):
                raise ValueError("CORS origins must be explicit HTTP(S) origins without paths")
        return values

    @property
    def resolved_database_url(self) -> URL:
        url = make_url(self.database_url)
        if url.database == ":memory:":
            return url
        path = Path(str(url.database))
        if not path.is_absolute():
            path = self.casetrace_root / path
        return url.set(database=str(path.resolve()))

    @property
    def resolved_asset_path(self) -> Path:
        path = self.asset_storage_path
        return (path if path.is_absolute() else self.casetrace_root / path).resolve()


class SettingsOverrides(TypedDict, total=False):
    casetrace_root: Path
    app_env: Literal["development", "test", "production"]
    api_host: str
    api_port: int
    database_url: str
    sqlite_busy_timeout_ms: int
    asset_storage_path: Path
    cors_allowed_origins: list[str]
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def load_settings(**overrides: Unpack[SettingsOverrides]) -> Settings:
    # Explicit root overrides also select the matching root .env file.
    root = (
        Path(str(overrides["casetrace_root"])) if "casetrace_root" in overrides else default_root()
    )

    class RootSettings(Settings):
        model_config = SettingsConfigDict(env_file=root / ".env", env_file_encoding="utf-8")

    return RootSettings(**overrides)
