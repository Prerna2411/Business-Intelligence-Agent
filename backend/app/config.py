from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Business Intelligence Agent")
    environment: str = os.getenv("ENVIRONMENT", "development")
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    top_k_memories: int = int(os.getenv("TOP_K_MEMORIES", "3"))

    groq_api_key: str | None = os.getenv("GROQ_API_KEY")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    clickhouse_host: str | None = os.getenv("CLICKHOUSE_HOST")
    clickhouse_port: int = int(os.getenv("CLICKHOUSE_PORT", "8443"))
    clickhouse_user: str | None = os.getenv("CLICKHOUSE_USER")
    clickhouse_password: str | None = os.getenv("CLICKHOUSE_PASSWORD")
    clickhouse_database: str = os.getenv("CLICKHOUSE_DATABASE", "default")
    clickhouse_secure: bool = os.getenv("CLICKHOUSE_SECURE", "true").lower() == "true"
    chroma_path: str = os.getenv("CHROMA_PATH", "data/vector_store/chroma")
    uploads_path: str = os.getenv("UPLOADS_PATH", "data/uploads")
    sparse_index_path: str = os.getenv("SPARSE_INDEX_PATH", "data/sparse_index/index.json")
    rag_chunk_size: int = int(os.getenv("RAG_CHUNK_SIZE", "800"))
    rag_chunk_overlap: int = int(os.getenv("RAG_CHUNK_OVERLAP", "120"))
    rag_top_k: int = int(os.getenv("RAG_TOP_K", "5"))

    @property
    def has_groq_api_key(self) -> bool:
        return bool(self.groq_api_key)

    @property
    def has_clickhouse_credentials(self) -> bool:
        return bool(self.clickhouse_host and self.clickhouse_user and self.clickhouse_password)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
