# Samba tenant deployer and dashboard

A Python conversion of the Bash workflow plus a Flask dashboard showing:

- container name
- `healthy` / `unhealthy` status
- domain name
- LDAP domain URL (`ldap://domain:published-port`)
- default account patterns: `admin@domainname` and `consumer@domainname`
- published port and Docker container state

## Deploy tenants

Run on the Docker host:

```bash
cd /opt/samba-tenant-dashboard
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export SAMBA_PASSWORD='use-a-strong-secret'
python deploy.py
```

To also perform the original host preparation steps, run:

```bash
sudo -E .venv/bin/python deploy.py --prepare-host
```

`--prepare-host` changes firewalld/SELinux settings and may install Docker. Use it only when that is intended for the host.

## Run the dashboard directly

The dashboard must be able to read the Docker socket:

```bash
python app.py
```

Open <http://localhost:8080>. The API is available at `/api/tenants`; `/healthz` is a process health endpoint.

## Run the dashboard with Docker Compose

```bash
docker compose -f docker-compose.yml up -d --build
```

The compose service mounts the Docker socket read-only. Do not expose port 8080 publicly without adding authentication and TLS.

## Health behavior

The generated base image includes a Docker `HEALTHCHECK` that verifies Samba's LDAP port inside the container. If an existing container has no Docker healthcheck, the dashboard falls back to testing the published host port. A missing, stopped, or unreachable container is shown as `unhealthy`.

## Important security note

The original script uses a shared password for all tenants. This version requires `SAMBA_PASSWORD` instead of placing the password in source code, but the password is still passed to the container as an environment variable to preserve the original container behavior. For production, use a secret store and unique credentials per tenant.
