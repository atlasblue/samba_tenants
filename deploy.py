#!/usr/bin/env python3
"""Provision the Samba AD tenant containers from the original Bash workflow.

This command is intentionally separate from the dashboard. Run it only on the
Docker host, with Docker available and SAMBA_PASSWORD set in the environment.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

import docker
from docker.errors import APIError, BuildError, NotFound

from config import DEFAULT_DOMAINS, SETTINGS

ENTRYPOINT_PY = r'''#!/usr/bin/env python3
import os
import subprocess


def run(command):
    subprocess.run(command, check=True)


if not os.path.exists('/etc/samba/smb.conf'):
    run([
        'samba-tool', 'domain', 'provision',
        f"--realm={os.environ['DOMAIN']}",
        f"--domain={os.environ['NETBIOS']}",
        f"--adminpass={os.environ['PASS']}",
        '--server-role=dc', '--dns-backend=NONE',
    ])
    smb_conf = '/etc/samba/smb.conf'
    content = open(smb_conf).read()
    content = content.replace('[global]', '[global]\n    ldap server require strong auth = no', 1)
    open(smb_conf, 'w').write(content)
    for user in os.environ.get('USER_LIST', '').split():
        run(['samba-tool', 'user', 'create', user, os.environ['PASS']])

os.execv('/usr/sbin/samba', ['/usr/sbin/samba', '-i'])
'''

DOCKERFILE = r'''FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y python3 samba smbclient winbind && rm -rf /var/lib/apt/lists/*
COPY entrypoint.py /entrypoint.py
RUN chmod +x /entrypoint.py
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 CMD bash -c 'echo > /dev/tcp/127.0.0.1/389' || exit 1
ENTRYPOINT ["python3", "/entrypoint.py"]
''' 


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("$", " ".join(command))
    return subprocess.run(command, check=check, text=True)


def prepare_host() -> None:
    """Apply the same host preparation as the Bash script when requested."""
    if os.geteuid() != 0:
        raise PermissionError("--prepare-host must be run as root")

    run(["systemctl", "disable", "--now", "firewalld"], check=False)
    run(["setenforce", "0"], check=False)
    selinux_config = Path("/etc/selinux/config")
    if selinux_config.exists():
        content = selinux_config.read_text()
        content = content.replace("SELINUX=enforcing", "SELINUX=disabled").replace(
            "SELINUX=permissive", "SELINUX=disabled"
        )
        selinux_config.write_text(content)

    if shutil.which("docker") is None:
        run(["dnf", "config-manager", "--add-repo=https://download.docker.com/linux/centos/docker-ce.repo"])
        run(["dnf", "install", "-y", "docker-ce", "docker-ce-cli", "containerd.io"])
    run(["systemctl", "enable", "--now", "docker"], check=False)


def build_base_image(client: docker.DockerClient) -> None:
    build_dir = SETTINGS.base_dir / "base"
    build_dir.mkdir(parents=True, exist_ok=True)
    (build_dir / "entrypoint.py").write_text(ENTRYPOINT_PY)
    (build_dir / "Dockerfile").write_text(DOCKERFILE)
    print(f"Building {SETTINGS.base_image}...")
    try:
        image, logs = client.images.build(
            path=str(build_dir), tag=SETTINGS.base_image, rm=True, pull=True
        )
        for item in logs:
            if "stream" in item:
                print(item["stream"], end="")
        print(f"Built {image.tags[0] if image.tags else SETTINGS.base_image}")
    except BuildError as exc:
        for item in exc.build_log:
            if "stream" in item:
                print(item["stream"], end="")
        raise


def deploy_tenant(client: docker.DockerClient, domain: str, port: int) -> None:
    tenant_dir = SETTINGS.base_dir / domain
    (tenant_dir / "data").mkdir(parents=True, exist_ok=True)
    (tenant_dir / "config").mkdir(parents=True, exist_ok=True)

    try:
        existing = client.containers.get(domain)
        print(f"Skipping {domain}: container already exists ({existing.status})")
        return
    except NotFound:
        pass

    print(f"Deploying {domain} on port {port}...")
    netbios = domain.split(".", 1)[0].upper()
    client.containers.run(
        SETTINGS.base_image,
        name=domain,
        privileged=True,
        detach=True,
        restart_policy={"Name": "unless-stopped"},
        ports={"389/tcp": port},
        volumes={
            str(tenant_dir / "data"): {"bind": "/var/lib/samba", "mode": "rw"},
            str(tenant_dir / "config"): {"bind": "/etc/samba", "mode": "rw"},
        },
        environment={
            "DOMAIN": domain,
            "NETBIOS": netbios,
            "PASS": SETTINGS.password,
            "USER_LIST": " ".join(SETTINGS.users),
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--prepare-host",
        action="store_true",
        help="disable firewalld/SELinux and install/start Docker when needed",
    )
    parser.add_argument("--skip-build", action="store_true", help="reuse the existing base image")
    args = parser.parse_args()

    if not SETTINGS.password:
        print("Set SAMBA_PASSWORD before deploying; refusing to use an empty password.", file=sys.stderr)
        return 2
    if args.prepare_host:
        prepare_host()

    try:
        client = docker.from_env()
        client.ping()
        if not args.skip_build:
            build_base_image(client)
        for domain, port in DEFAULT_DOMAINS:
            deploy_tenant(client, domain, port)
    except (APIError, docker.errors.DockerException, OSError, PermissionError) as exc:
        print(f"Deployment failed: {exc}", file=sys.stderr)
        return 1

    print("Deployments finished successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
