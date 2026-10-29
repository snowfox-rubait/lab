#!/usr/bin/env bash
# ==============================================================================
# Installer Script for Short Links Manager inside Proxmox LXC 225 (vmbr1)
# ==============================================================================
set -euo pipefail

INSTALL_DIR="/opt/short-manager"
SERVICE_NAME="short-manager.service"

echo "=================================================="
echo "⚡ Installing Snowfox Short Links Manager..."
echo "Target: ${INSTALL_DIR}"
echo "=================================================="

# Check root
if [ "$(id -u)" -ne 0 ]; then
  echo "[-] Error: This script must be run as root inside the LXC container."
  exit 1
fi

# Ensure python3 is installed
if ! command -v python3 >/dev/null 2>&1; then
  echo "[*] Installing Python 3..."
  apt-get update -qq && apt-get install -y -qq python3
fi

# Create directory
mkdir -p "${INSTALL_DIR}"

# Copy files
echo "[*] Copying application files..."
cp app.py "${INSTALL_DIR}/app.py"
chmod +x "${INSTALL_DIR}/app.py"

if [ ! -f "${INSTALL_DIR}/.env" ]; then
  if [ -f .env ]; then
    cp .env "${INSTALL_DIR}/.env"
  else
    cp .env.example "${INSTALL_DIR}/.env"
    echo "[!] Created default .env at ${INSTALL_DIR}/.env. Please configure your SHORTENER_SECRET_TOKEN."
  fi
  chmod 600 "${INSTALL_DIR}/.env"
fi

# Install systemd service
echo "[*] Configuring systemd service..."
cp "${SERVICE_NAME}" "/etc/systemd/system/${SERVICE_NAME}"
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
systemctl restart "${SERVICE_NAME}"

echo "=================================================="
echo "✅ Short Links Manager installed and running!"
echo "Check status: systemctl status ${SERVICE_NAME}"
echo "Local URL:    http://10.10.10.35:8080 or http://short.internal.lab:8080"
echo "=================================================="
