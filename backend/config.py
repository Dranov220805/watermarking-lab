"""Environment-driven settings for the DCT watermarking backend.

Precedence: OS environment variables > .env.local > .env > defaults.
"""
from dataclasses import dataclass
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

_BASE_DIR = Path(__file__).resolve().parent


def _load_env_files(env_dir: Optional[Path] = None) -> None:
    base = env_dir or _BASE_DIR
    env_local = base / ".env.local"
    env_file = base / ".env"
    if env_local.is_file():
        load_dotenv(env_local, override=False)
    if env_file.is_file():
        load_dotenv(env_file, override=False)


def _env_str(name: str, default: str, fallback: Optional[str] = None) -> str:
    val = os.environ.get(name)
    if val is None and fallback:
        val = os.environ.get(fallback)
    return val.strip() if val is not None and val.strip() != "" else default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    return int(raw.strip()) if raw is not None and raw.strip() != "" else default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    return float(raw.strip()) if raw is not None and raw.strip() != "" else default


@dataclass(frozen=True)
class Settings:
    app_host: str
    app_port: int
    app_title: str
    cors_origins: tuple[str, ...]
    storage_dir: Optional[str]
    storage_ttl_seconds: int
    cleanup_interval_seconds: int
    max_upload_mb: int
    default_alpha: float
    default_null_trials: int
    max_null_trials: int

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


def load_settings(env_dir: Optional[Path] = None) -> Settings:
    _load_env_files(env_dir)
    raw_cors = _env_str("CORS_ORIGINS", "http://localhost:3000", fallback="WM_CORS")
    cors_origins = tuple(o.strip() for o in raw_cors.split(",") if o.strip())
    raw_store = _env_str("STORAGE_DIR", "", fallback="WM_STORE")
    return Settings(
        app_host=_env_str("APP_HOST", "127.0.0.1"),
        app_port=_env_int("APP_PORT", 8000),
        app_title=_env_str("APP_TITLE", "DCT watermark API"),
        cors_origins=cors_origins,
        storage_dir=raw_store or None,
        storage_ttl_seconds=_env_int("STORAGE_TTL_SECONDS", 7200),
        cleanup_interval_seconds=_env_int("CLEANUP_INTERVAL_SECONDS", 600),
        max_upload_mb=_env_int("MAX_UPLOAD_MB", 100),
        default_alpha=_env_float("DEFAULT_ALPHA", 25.0),
        default_null_trials=_env_int("DEFAULT_NULL_TRIALS", 40),
        max_null_trials=_env_int("MAX_NULL_TRIALS", 200),
    )


settings = load_settings()
