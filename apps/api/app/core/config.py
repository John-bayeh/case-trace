"""Application configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    # Environment
    ENVIRONMENT: Literal["development", "production", "test"] = "development"
    DEBUG: bool = True
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_PREFIX: str = "/api"
    
    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:3001"]
    
    # Database - Absolute path resolution per development-stack.md
    PROJECT_ROOT: Path = Path(__file__).parent.parent.parent.parent.parent
    DATABASE_URL: str = ""
    
    def __init__(self, **kwargs):  # type: ignore
        super().__init__(**kwargs)
        # Resolve absolute database path
        if not self.DATABASE_URL:
            db_path = self.PROJECT_ROOT / "data" / "runtime" / "casetrace.db"
            self.DATABASE_URL = f"sqlite+aiosqlite:///{db_path.absolute()}"
    
    # LLM Provider
    LLM_PROVIDER: Literal["gemini", "openai", "anthropic", "local"] = "gemini"
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    
    # Investigation
    INVESTIGATION_TIMEOUT: int = 300  # seconds
    MAX_AGENT_ITERATIONS: int = 10
    MAX_TOOL_CALLS_PER_AGENT: int = 20
    
    # Evidence
    MIN_EVIDENCE_CONFIDENCE: float = 0.6
    
    # Assets
    ASSETS_DIR: Path = PROJECT_ROOT / "data" / "assets"
    CASES_DIR: Path = PROJECT_ROOT / "data" / "cases"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
