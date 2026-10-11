"""Environment-driven configuration (12-factor style)."""

from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import Any


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_config() -> dict[str, Any]:
    """Build the Flask configuration from environment variables.

    ``ACEEST_SECRET_KEY`` should always be set in shared environments; when it
    is missing a random key is generated so that no predictable secret ships
    with the image (sessions then reset on restart).
    """
    admin_password = os.environ.get("ACEEST_ADMIN_PASSWORD")
    return {
        "SECRET_KEY": os.environ.get("ACEEST_SECRET_KEY") or secrets.token_hex(32),
        "DATABASE": os.environ.get("ACEEST_DB_PATH") or str(Path.cwd() / "instance" / "aceest.db"),
        "ADMIN_USERNAME": os.environ.get("ACEEST_ADMIN_USERNAME", "admin"),
        # Legacy default kept for demos only; a warning is logged when it is used.
        "ADMIN_PASSWORD": admin_password or "admin",
        "ADMIN_PASSWORD_IS_DEFAULT": not admin_password,
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": _env_flag("ACEEST_SECURE_COOKIES"),
    }
