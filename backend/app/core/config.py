from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str
    gemini_model: str = "gemini-2.5-flash"
    # Cheaper model for offline jobs (schema-indexer table descriptions).
    # Live /query stays on flash; lite preserves the 20 RPD flash budget.
    gemini_indexer_model: str = "gemini-2.5-flash-lite"
    embed_model: str = "gemini-embedding-001"
    embed_dim: int = 768
    supabase_db_url: str = ""
    # Groq runtime fallback. Empty key disables the fallback — generate_sql
    # then propagates Gemini's 429/5xx upstream like before. When set, the
    # eval and live /query keep working after Gemini's daily cap is hit.
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
