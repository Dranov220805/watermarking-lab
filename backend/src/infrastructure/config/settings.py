"""Centralized environment-driven configuration for WM.WatermarkService.

Loads `.env` and `.env.local` (with `.env.local` overriding `.env`, and OS environment
variables always taking highest precedence).
"""
from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from src.domain_shared.consts import (
    API_PREFIX,
    API_VERSION,
    CLEANUP_INTERVAL_SECONDS,
    DEFAULT_ALPHA,
    MAX_NULL_TRIALS,
    MAX_UPLOAD_BYTES,
    SYSTEM_NAME,
    TTL_SECONDS,
)

_BACKEND_ROOT = Path(__file__).resolve().parents[3]


def _load_env_files(env_dir: Optional[Path] = None) -> None:
    base = env_dir or _BACKEND_ROOT
    env_file = base / ".env"
    env_local_file = base / ".env.local"
    # Load .env.local first (override=False keeps OS env vars highest priority),
    # then .env for any keys not already set in OS or .env.local.
    if env_local_file.is_file():
        load_dotenv(env_local_file, override=False)
    if env_file.is_file():
        load_dotenv(env_file, override=False)


def _env_str(name: str, default: str, fallback_name: Optional[str] = None) -> str:
    val = os.environ.get(name)
    if val is None and fallback_name:
        val = os.environ.get(fallback_name)
    return val.strip() if val is not None and val.strip() != "" else default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw.strip())


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return float(raw.strip())


@dataclass(frozen=True)
class Settings:
    app_host: str
    app_port: int
    system_name: str
    api_prefix: str
    api_version: str
    cors_origins: tuple[str, ...]
    storage_dir: Optional[str]
    storage_ttl_seconds: int
    cleanup_interval_seconds: int
    max_upload_mb: int
    default_alpha: float
    default_null_trials: int
    max_null_trials: int

    @property
    def api_base_path(self) -> str:
        prefix = "/" + self.api_prefix.strip("/")
        version = self.api_version.strip("/")
        return f"{prefix}/{version}"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


def load_settings(env_dir: Optional[Path] = None) -> Settings:
    _load_env_files(env_dir)

    raw_cors = _env_str("CORS_ORIGINS", "http://localhost:3000", fallback_name="WM_CORS")
    cors_origins = tuple(origin.strip() for origin in raw_cors.split(",") if origin.strip())

    raw_storage = _env_str("STORAGE_DIR", "", fallback_name="WM_STORE")
    default_max_mb = MAX_UPLOAD_BYTES // (1024 * 1024)

    return Settings(
        app_host=_env_str("APP_HOST", "127.0.0.1"),
        app_port=_env_int("APP_PORT", 8000),
        system_name=_env_str("SYSTEM_NAME", SYSTEM_NAME),
        api_prefix=_env_str("API_PREFIX", API_PREFIX),
        api_version=_env_str("API_VERSION", API_VERSION),
        cors_origins=cors_origins,
        storage_dir=raw_storage or None,
        storage_ttl_seconds=_env_int("STORAGE_TTL_SECONDS", TTL_SECONDS),
        cleanup_interval_seconds=_env_int("CLEANUP_INTERVAL_SECONDS", CLEANUP_INTERVAL_SECONDS),
        max_upload_mb=_env_int("MAX_UPLOAD_MB", default_max_mb),
        default_alpha=_env_float("DEFAULT_ALPHA", DEFAULT_ALPHA),
        default_null_trials=_env_int("DEFAULT_NULL_TRIALS", 40),
        max_null_trials=_env_int("MAX_NULL_TRIALS", MAX_NULL_TRIALS),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()
