"""Shared configuration for the Samba tenant deployer and dashboard."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DOMAINS = [
    ("acme.fr", 3891),
    ("nova.fr", 3892),
    ("alpha.com", 3893),
    ("beta.fr", 3894),
    ("delta.com", 3895),
    ("zenith.fr", 3896),
    ("atlas.com", 3897),
    ("orion.fr", 3898),
    ("nexus.com", 3899),
    ("vertex.fr", 3900),
]


@dataclass(frozen=True)
class Settings:
    base_dir: Path = Path(os.getenv("SAMBA_BASE_DIR", "/opt/samba-tenants"))
    base_image: str = os.getenv("SAMBA_BASE_IMAGE", "samba-base")
    users: tuple[str, ...] = tuple(
        value for value in os.getenv("SAMBA_USERS", "admin,consumer").split(",") if value
    )
    password: str = os.getenv("SAMBA_PASSWORD", "")
    dashboard_host: str = os.getenv("DASHBOARD_HOST", "0.0.0.0")
    dashboard_port: int = int(os.getenv("DASHBOARD_PORT", "8080"))
    dashboard_refresh_seconds: int = int(os.getenv("DASHBOARD_REFRESH_SECONDS", "15"))


SETTINGS = Settings()
