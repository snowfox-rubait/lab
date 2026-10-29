#!/bin/sh
# ==============================================================================
# OpenWrt Split-Horizon DNS & Anti-Rebinding Configuration
# Configures dnsmasq on OpenWrt (Physical Router 192.168.1.1 or VM 192.168.1.129)
# Resolves private *.snowfox.live services to nginx-safe (10.10.10.10)
# ==============================================================================
set -e

NGINX_SAFE_IP="10.10.10.10"
DOMAIN="snowfox.live"

echo "=================================================="
echo "⚡ OpenWrt Split-Horizon DNS Setup for ${DOMAIN}"
echo "Reverse Proxy Target: ${NGINX_SAFE_IP}"
echo "=================================================="

# 1. Whitelist snowfox.live from DNS Rebinding Protection
# Prevents dnsmasq from dropping private RFC1918 responses for public domains
echo "[1/3] Adding '${DOMAIN}' to DNS Rebinding Whitelist..."
uci del_list dhcp.@dnsmasq[0].rebind_domain="${DOMAIN}" 2>/dev/null || true
uci add_list dhcp.@dnsmasq[0].rebind_domain="${DOMAIN}"

# 2. Add Authoritative Internal Service Records
# Targeted hostnames mapped to nginx-safe reverse proxy (10.10.10.10)
# Note: Public hostnames (e.g. short.snowfox.live, root snowfox.live) are NOT
# mapped here, allowing them to resolve to Cloudflare Edge normally.
SERVICES="pve router wan pihole gitea n8n short-admin photos ha internal"

echo "[2/3] Configuring internal service DNS records..."
for s in ${SERVICES}; do
    RECORD="/${s}.${DOMAIN}/${NGINX_SAFE_IP}"
    uci del_list dhcp.@dnsmasq[0].address="${RECORD}" 2>/dev/null || true
    uci add_list dhcp.@dnsmasq[0].address="${RECORD}"
    echo "  -> ${s}.${DOMAIN} => ${NGINX_SAFE_IP}"
done

# 3. Commit and Reload dnsmasq
echo "[3/3] Committing UCI changes and reloading dnsmasq..."
uci commit dhcp
/etc/init.d/dnsmasq reload

echo "=================================================="
echo "✅ Split-Horizon DNS successfully configured!"
echo "Test on LAN: nslookup gitea.snowfox.live"
echo "=================================================="
