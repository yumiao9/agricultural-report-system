"""Application configuration loaded from environment variables."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).parent.parent / ".env")


class Settings:
    """Application settings."""

    # LLM
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    REPORT_LLM: str = os.getenv("REPORT_LLM", "deepseek")  # "deepseek" or "claude"

    # Search
    SEARCH_BACKEND: str = os.getenv("SEARCH_BACKEND", "duckduckgo")
    SEARCH_MAX_RESULTS: int = int(os.getenv("SEARCH_MAX_RESULTS", "12"))
    SERPAPI_API_KEY: str = os.getenv("SERPAPI_API_KEY", "")
    BRAVE_SEARCH_API_KEY: str = os.getenv("BRAVE_SEARCH_API_KEY", "")
    BING_API_KEY: str = os.getenv("BING_API_KEY", "")

    # Chinese search
    ENABLE_BAIDU: bool = os.getenv("ENABLE_BAIDU", "true").lower() == "true"
    ENABLE_CHINESE_OFFICIAL: bool = os.getenv("ENABLE_CHINESE_OFFICIAL", "true").lower() == "true"

    # Application
    _raw_db_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/reports.db")
    DATABASE_URL: str = (
        _raw_db_url
        .replace("postgresql://", "postgresql+asyncpg://")
        .replace("postgres://", "postgresql+asyncpg://")
        .replace("?channel_binding=require", "")
        .replace("&channel_binding=require", "")
        .replace("?sslmode=require", "?ssl=require")
        .replace("&sslmode=require", "&ssl=require")
    ) if _raw_db_url.startswith("postgresql") or _raw_db_url.startswith("postgres") else _raw_db_url
    CACHE_TTL_HOURS: int = int(os.getenv("CACHE_TTL_HOURS", "168"))
    SEARCH_TIMEOUT_SECONDS: int = int(os.getenv("SEARCH_TIMEOUT_SECONDS", "120"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Project paths
    BASE_DIR: Path = Path(__file__).parent.parent
    _data_dir_env = os.getenv("DATA_DIR", "")
    DATA_DIR: Path = Path(_data_dir_env) if _data_dir_env else BASE_DIR / "data"
    STATIC_DIR: Path = Path(__file__).parent / "static"
    TEMPLATES_DIR: Path = Path(__file__).parent / "templates"

    @property
    def is_configured(self) -> bool:
        """Check if required API keys are set."""
        if not self.DEEPSEEK_API_KEY:
            return False
        return True

    @property
    def llm_config(self) -> dict:
        """Get the primary LLM configuration."""
        if self.REPORT_LLM == "claude" and self.ANTHROPIC_API_KEY:
            return {
                "provider": "claude",
                "api_key": self.ANTHROPIC_API_KEY,
                "model": self.ANTHROPIC_MODEL,
            }
        return {
            "provider": "deepseek",
            "api_key": self.DEEPSEEK_API_KEY,
            "base_url": self.DEEPSEEK_BASE_URL,
            "model": self.DEEPSEEK_MODEL,
        }


settings = Settings()
