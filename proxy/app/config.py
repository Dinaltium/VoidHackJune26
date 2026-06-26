"""Runtime configuration, loaded from environment / .env.

Everything degrades gracefully: with no GROQ_API_KEY the proxy still runs and
enforces the deterministic + heuristic layers offline. Model-backed layers
(Prompt Guard 2, gpt-oss-safeguard) light up only when a key is present.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root = .../VoidHackJune26 ; this file is proxy/app/config.py
REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Firewall settings. Override any field via env var of the same name."""

    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", Path(".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- upstream provider (OpenAI-compatible; Groq by default) ---
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    upstream_timeout_s: float = 60.0

    # --- model ids (all free-tier on Groq) ---
    victim_model: str = "llama-3.3-70b-versatile"
    promptguard_model: str = "meta-llama/llama-prompt-guard-2-86m"
    safeguard_model: str = "openai/gpt-oss-safeguard-20b"

    # --- feature toggles ---
    enable_groq_promptguard: bool = True   # use Prompt Guard 2 when key present
    enable_safeguard_judge: bool = True     # use gpt-oss-safeguard on flagged actions
    enable_presidio: bool = False           # optional heavy PII engine (regex used otherwise)

    # --- policy + storage ---
    policy_path: Path = REPO_ROOT / "policies" / "policy.yaml"
    db_path: Path = REPO_ROOT / "proxy" / "firewall.sqlite"
    hmac_secret: str = "dev-insecure-change-me"  # signs receipts; override in prod

    # --- server ---
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @property
    def groq_enabled(self) -> bool:
        return bool(self.groq_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
