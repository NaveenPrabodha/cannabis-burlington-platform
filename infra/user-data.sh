#!/bin/bash
# EC2 user-data bootstrap script. Paste this into the "Advanced details →
# User data" field when launching the EC2 instance. It runs once at first boot
# and installs everything the host needs to run docker-compose.

set -euxo pipefail

# Update packages
dnf update -y

# Install Docker
dnf install -y docker
systemctl enable --now docker
usermod -aG docker ec2-user

# Install Docker Compose plugin (it's now part of the Docker CLI)
mkdir -p /usr/local/lib/docker/cli-plugins
COMPOSE_VERSION=v2.32.0
curl -SL "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-linux-x86_64" \
    -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Useful tools
dnf install -y git htop tmux

# Swap (t3.micro has only 1GB RAM — swap helps the Next.js build not OOM)
dd if=/dev/zero of=/swapfile bs=1M count=2048
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo "/swapfile none swap sw 0 0" >> /etc/fstab

# Friendly login message
cat > /etc/motd <<'EOF'
═══════════════════════════════════════════════════════════════
 Burlington Cannabis Platform — EC2 host
   git clone https://github.com/DKLOCHANA/cannabis-burlington-platform.git
   cd cannabis-burlington-platform/infra
   cp .env.example .env  # then edit
   docker compose --profile prod up -d
═══════════════════════════════════════════════════════════════
EOF

echo "user-data complete at $(date -u)"
