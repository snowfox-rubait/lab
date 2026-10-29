#!/usr/bin/env bash
# ==============================================================================
# Cloudflare Worker & KV Namespace Deployment Helper
# Target Domain: short.snowfox.live
# ==============================================================================
set -euo pipefail

echo "=================================================="
echo "⚡ Cloudflare Edge Worker Setup: short.snowfox.live"
echo "=================================================="

# Check for wrangler
if ! command -v wrangler >/dev/null 2>&1 && ! command -v npx >/dev/null 2>&1; then
  echo "[-] Error: wrangler or npx is required. Install Node.js & npm first."
  exit 1
fi

echo "[1/4] Checking Cloudflare authentication..."
npx wrangler whoami || {
  echo "[!] Please log into Cloudflare via: npx wrangler login"
  exit 1
}

echo "[2/4] Setting up KV Namespace 'SHORT_LINKS'..."
echo "Run this command to create the KV store if you haven't already:"
echo "    npx wrangler kv namespace create SHORT_LINKS"
echo "Then copy the namespace ID into wrangler.toml under 'kv_namespaces'."
echo ""

echo "[3/4] Setting up Master Authorization Secret..."
echo "Enter your secure master authorization token:"
npx wrangler secret put SHORTENER_SECRET_TOKEN

echo "[4/4] Deploying Worker to Cloudflare Edge..."
npx wrangler deploy

echo "=================================================="
echo "✅ Cloudflare Worker deployed successfully!"
echo "Target: https://short.snowfox.live"
echo "=================================================="
