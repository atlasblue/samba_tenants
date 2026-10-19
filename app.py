#!/usr/bin/env python3
"""Flask dashboard for Samba tenant container health."""
from __future__ import annotations

import socket
from datetime import datetime, timezone
from typing import Any

import docker
from docker.errors import DockerException, NotFound
from flask import Flask, jsonify, render_template

from config import DEFAULT_DOMAINS, SETTINGS

app = Flask(__name__)


def port_for(domain: str) -> int | None:
    return next((port for name, port in DEFAULT_DOMAINS if name == domain), None)


def fallback_port_health(port: int | None) -> str:
    if port is None:
        return "unhealthy"
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1.5):
            return "healthy"
    except OSError:
        return "unhealthy"


def health_for(container: Any, port: int | None) -> str:
    attrs = container.attrs.get("State", {})
    docker_health = attrs.get("Health", {}).get("Status")
    if docker_health == "healthy":
        return "healthy"
    if docker_health in {"unhealthy", "dead", "starting"}:
        return "unhealthy"
    if attrs.get("Running"):
        return fallback_port_health(port)
    return "unhealthy"


def tenant_row(container: Any) -> dict[str, Any]:
    name = container.name
    port = port_for(name)
    return {
        "container_name": name,
        "status": health_for(container, port),
        "container_state": container.attrs.get("State", {}).get("Status", "unknown"),
        "domain_name": name,
        "domain_url": f"ldap://{name}:{port}" if port else None,
        "port": port,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def get_tenants() -> dict[str, Any]:
    expected = {domain: port for domain, port in DEFAULT_DOMAINS}
    try:
        client = docker.from_env()
        containers = {container.name: container for container in client.containers.list(all=True)}
        rows = []
        for domain, port in DEFAULT_DOMAINS:
            container = containers.get(domain)
            if container is None:
                rows.append(
                    {
                        "container_name": domain,
                        "status": "unhealthy",
                        "container_state": "missing",
                        "domain_name": domain,
                        "domain_url": f"ldap://{domain}:{port}",
                        "port": port,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
            else:
                rows.append(tenant_row(container))
        return {"tenants": rows, "error": None}
    except DockerException as exc:
        return {
            "tenants": [
                {
                    "container_name": domain,
                    "status": "unhealthy",
                    "container_state": "docker unavailable",
                    "domain_name": domain,
                    "domain_url": f"ldap://{domain}:{port}",
                    "port": port,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
                for domain, port in expected.items()
            ],
            "error": f"Docker unavailable: {exc}",
        }


@app.get("/")
def index():
    return render_template(
        "index.html",
        refresh_seconds=SETTINGS.dashboard_refresh_seconds,
        tenant_count=len(DEFAULT_DOMAINS),
    )


@app.get("/api/tenants")
def api_tenants():
    return jsonify(get_tenants())


@app.get("/healthz")
def healthz():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host=SETTINGS.dashboard_host, port=SETTINGS.dashboard_port)
