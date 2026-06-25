"""
Centralised configuration — all values come from environment variables.
Never hardcode secrets. Copy .env.example → .env and fill in your values.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = "sqlite:///./scanner.db"
    # CRM Excel Processor — separate DB (ctr_db)
    crm_database_url: str = "sqlite:///./ctr_app.db"

    # ── Security ──────────────────────────────────────────────────────────────
    # Set API_KEY in .env to protect endpoints. Leave empty to disable (dev only).
    api_key: str = ""

    # ── AI Vision ─────────────────────────────────────────────────────────────
    # Claude Vision — AI-powered ad slot detection. Set in .env.
    anthropic_api_key: str = ""

    # ── Browser engine ────────────────────────────────────────────────────────
    engine_nav_timeout_ms: int = 45_000
    # Cloud RAM guide: free tier (512 MB) → 3, starter (2 GB) → 8, standard (4 GB) → 20
    # Default 8 — safe for Render Standard. Override via ENGINE_CONCURRENCY env var.
    engine_concurrency: int = 8
    headless: bool = True

    # ── Paths (relative to Backend_Screenshot/) ───────────────────────────────
    # Override these with absolute paths when using a Render persistent disk.
    # Example: SCREENSHOTS_DIR=/app/data/screenshots
    screenshots_dir: str = "screenshots"
    input_images_dir: str = "../input_images"
    ppt_assets_dir: str = "ppt_assets"
    processed_outputs_dir: str = "processed_outputs"   # CRM processed CSV files

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Comma-separated list of allowed origins in production.
    # Example: "https://your-app.netlify.app,https://admin.example.com"
    # Leave empty to allow all origins (dev only).
    allowed_origins: str = ""

    # ── App ───────────────────────────────────────────────────────────────────
    app_env: str = "development"   # "development" | "production"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached Settings singleton. Use this everywhere."""
    return Settings()
