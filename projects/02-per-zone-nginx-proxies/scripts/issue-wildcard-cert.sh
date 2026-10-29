#!/usr/bin/env bash
# ==============================================================================
# Automated Let's Encrypt Wildcard SSL/TLS Certificate Provisioner
# Domain: *.snowfox.live & snowfox.live
# Challenge: Cloudflare DNS-01 (Zero open inbound ports required)
# Runs on: LXC 201 (nginx-safe on 10.10.10.10)
# ==============================================================================
set -euo pipefail

DOMAIN="snowfox.live"
WILDCARD="*.${DOMAIN}"
CERT_DIR="/etc/letsencrypt/live/${DOMAIN}"
CLOUDFLARE_CREDENTIALS="/etc/letsencrypt/cloudflare.ini"

echo "=================================================="
echo "🔒 Wildcard SSL/TLS Certificate Generator (DNS-01)"
echo "Domain: ${WILDCARD} & ${DOMAIN}"
echo "=================================================="

# Check root execution
if [ "$(id -u)" -ne 0 ]; then
  echo "[-] Error: This script must be run as root."
  exit 1
fi

# Ensure certbot and python3-certbot-dns-cloudflare are installed
if ! command -v certbot >/dev/null 2>&1; then
  echo "[*] Installing Certbot and Cloudflare DNS plugin..."
  apt-get update -qq && apt-get install -y -qq certbot python3-certbot-dns-cloudflare
fi

# Check for Cloudflare API token credentials
if [ ! -f "${CLOUDFLARE_CREDENTIALS}" ]; then
  echo "[-] Error: Cloudflare credentials file missing at ${CLOUDFLARE_CREDENTIALS}"
  echo "Create ${CLOUDFLARE_CREDENTIALS} with 600 permissions containing:"
  echo "    dns_cloudflare_api_token = YOUR_CLOUDFLARE_API_TOKEN"
  echo ""
  echo "Required Token Permissions in Cloudflare Dashboard:"
  echo "    Zone -> DNS -> Edit"
  echo "    Zone Resources -> Include -> All zones (or snowfox.live)"
  exit 1
fi

chmod 600 "${CLOUDFLARE_CREDENTIALS}"

echo "[*] Requesting Wildcard Certificate from Let's Encrypt via DNS-01..."
certbot certonly \
  --dns-cloudflare \
  --dns-cloudflare-credentials "${CLOUDFLARE_CREDENTIALS}" \
  --dns-cloudflare-propagation-seconds 30 \
  -d "${WILDCARD}" \
  -d "${DOMAIN}" \
  --agree-tos \
  --non-interactive \
  --keep-until-expiring \
  --register-unsafely-without-email || {
    echo "[-] Certificate acquisition failed. Check Cloudflare token permissions and DNS propagation."
    exit 1
  }

echo "[*] Verifying certificate files..."
if [ -f "${CERT_DIR}/fullchain.pem" ] && [ -f "${CERT_DIR}/privkey.pem" ]; then
  echo "[+] Certificate acquired successfully at ${CERT_DIR}"
  
  # Reload Nginx if active
  if systemctl is-active --quiet nginx; then
    echo "[*] Reloading Nginx service..."
    nginx -t && systemctl reload nginx
    echo "[+] Nginx reloaded successfully with new certificate."
  fi
else
  echo "[-] Error: Certificate files not found at expected path."
  exit 1
fi

# Install automated daily renewal cron if not present
CRON_FILE="/etc/cron.d/certbot-wildcard-renew"
if [ ! -f "${CRON_FILE}" ]; then
  echo "[*] Setting up automatic renewal cron job..."
  cat <<'EOF' > "${CRON_FILE}"
# Daily certbot renewal check for wildcard certificate
0 3 * * * root certbot renew --quiet --post-hook "systemctl reload nginx"
EOF
  chmod 644 "${CRON_FILE}"
  echo "[+] Daily renewal cron installed at ${CRON_FILE}"
fi

echo "=================================================="
echo "✅ Wildcard certificate ready for *.snowfox.live!"
echo "=================================================="
