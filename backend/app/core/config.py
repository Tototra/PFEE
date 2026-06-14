"""Configuration centralisée du backend Coach IA GTB.

Charge les variables d'environnement via Pydantic Settings.
Toutes les valeurs sensibles (clés API, credentials) DOIVENT venir de .env.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings de l'application. Toutes ces valeurs viennent de .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Application ──────────────────────────────────────────────────────────
    app_name: str = "Coach IA GTB"
    app_env: Literal["dev", "staging", "prod"] = "dev"
    api_v1_prefix: str = "/api/v1"
    debug: bool = False
    log_level: str = "INFO"

    # ─── Sécurité ─────────────────────────────────────────────────────────────
    secret_key: str = Field(..., min_length=32)
    access_token_expire_minutes: int = 60 * 24  # 24h
    algorithm: str = "HS256"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ─── Base de données ──────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://coachia:coachia@localhost:5432/coachia"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # ─── Redis (cache + sessions) ─────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_default: int = 300  # 5 min

    # ─── Niagara (Couche C1) ──────────────────────────────────────────────────
    niagara_base_url: str = "https://niagara.aer.local"
    niagara_username: str = ""
    niagara_password: str = ""
    niagara_token: str | None = None
    niagara_verify_ssl: bool = True
    niagara_poll_interval_seconds: int = 30

    # ─── Anthropic / Claude (Couche C3 principale) ───────────────────────────
    # Pas de clé API nécessaire si on passe via le proxy Anthropic interne
    anthropic_api_key: str = ""          # laisser vide = utilise le proxy interne
    anthropic_model: str = "claude-sonnet-4-6"
    anthropic_max_tokens: int = 2000
    llm_temperature: float = 0.2

    # ─── Mistral (Couche C3 fallback — à activer quand la clé sera dispo) ────
    mistral_api_key: str = ""
    mistral_model: str = "mistral-large-latest"
    mistral_small_model: str = "mistral-small-latest"
    mistral_max_tokens: int = 2000

    # ─── Gemini (Couche C3 fallback secondaire) ───────────────────────────────
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-pro"

    # ─── Groq (fallback gratuit — Mixtral/Llama via API OpenAI-compatible) ────
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # ─── RAG ──────────────────────────────────────────────────────────────────
    chroma_persist_dir: str = "./data/chroma"
    embedding_model: str = "BAAI/bge-m3"
    rag_top_k: int = 5
    rag_chunk_size: int = 512
    rag_chunk_overlap: int = 50

    # ─── Open-Meteo (météo) ───────────────────────────────────────────────────
    openmeteo_base_url: str = "https://api.open-meteo.com/v1"
    weather_cache_ttl_seconds: int = 3600  # 1h

    # ─── Site par défaut (POC AER) ────────────────────────────────────────────
    default_site_lat: float = 48.8566
    default_site_lon: float = 2.3522
    default_site_timezone: str = "Europe/Paris"


@lru_cache
def get_settings() -> Settings:
    """Instance singleton des settings, mise en cache."""
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
