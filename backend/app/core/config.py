import os
from dataclasses import dataclass, field
from typing import List


def _parse_origins(raw_value: str) -> List[str]:
    if not raw_value:
        return ["*"]

    return [item.strip() for item in raw_value.split(",") if item.strip()]


@dataclass
class Settings:
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "AI Customer Service")
    VERSION: str = os.getenv("VERSION", "0.1.0")
    CORS_ORIGINS: List[str] = field(
        default_factory=lambda: _parse_origins(os.getenv("CORS_ORIGINS", "*"))
    )
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "sqlite+aiosqlite:///./aicustomer.db"
    )
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "deepseek-v4-flash")
    LLM_API_BASE: str = os.getenv("LLM_API_BASE", "https://api.deepseek.com")
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "512"))
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.3"))


settings = Settings()
