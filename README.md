# Samba Tenant Dashboard

Flask dashboard for Samba tenant containers.

## Dashboard columns

| Domain Name | Domain URL | Status | Admin User | Consumer User | Password |
|---|---|---|---|---|---|
| acme.fr | ldap://acme.fr:3891 | healthy | admin@acme.fr | consumer@acme.fr | Nutanix/4u |

The dashboard has no login password.

## Install on Ubuntu 24.04 and plus

### 1. Install prerequisites
```bash
sudo apt update
sudo apt install -y ca-certificates curl git python3 python3-venv python3-pip
```
### 2. Install Docker
```bash
sudo install -m 0755 -d /etc/apt/keyrings

sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc

sudo chmod a+r /etc/apt/keyrings/docker.asc

sudo tee /etc/apt/sources.list.d/docker.sources > /dev/null <<DOCKER_REPO
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
DOCKER_REPO

sudo apt update

sudo apt install -y docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin

sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
newgrp docker
```
### 3. Clone the project
```bash
sudo git clone https://github.com/atlasblue/samba_tenants.git \
  /opt/samba_tenant_dashboard

sudo chown -R "$USER:$USER" /opt/samba_tenant_dashboard
cd /opt/samba_tenant_dashboard
```
### 4. Configure Python
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
### 5. Configure the Samba password
```bash
echo "SAMBA_PASSWORD=Nutanix/4u" > .env
chmod 600 .env
set -a
source .env
set +a
```
### 6. Deploy Samba tenants
```bash
source .venv/bin/activate
python deploy.py
```
The Dashboard is available at http://SERVER_IP:8080

