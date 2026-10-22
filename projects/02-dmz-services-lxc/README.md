# 🛡️ DMZ Ingress & Reverse Proxy Architecture

> **Project:** `02-dmz-services-lxc`  
> **Target Network:** Proxmox Safe Zone Bridge (`vmbr1`, `10.10.10.0/24`)  
> **Core Components:** Hardened Nginx Reverse Proxy, Cloudflare Tunnel (`cloudflared`), Tailscale Split-DNS Ingress

---

## 🎯 Architecture Overview & Access Tiers

Services in our homelab are segregated into two distinct ingress tiers:

```
[ Internet User ]
       │
       ▼ (HTTPS / TLS 1.3)
[ Cloudflare Edge (*.snowfox.live) ]
       │
       ▼ (Encrypted QUIC Tunnel - No open router ports)
[ cloudflared Daemon ]
       │
       ▼ (Local Bridge / Origin CA SSL Full Strict)
[ Hardened Nginx Reverse Proxy (10.10.10.10) ]
       ├──▶ Vaultwarden (10.10.10.x:8085) [Public + Hardened Admin]
       ├──▶ Public Websites (10.10.10.x:3000) [Public]
       └──▶ MQTT Broker [Public / IoT Auth]

[ Tailscale User (Phone / PC) ]
       │
       ▼ (WireGuard Mesh 100.64.0.0/10 - Gray Cloud Cloudflare A-Record)
[ Nginx Virtual Hosts on Tailscale IP ]
       ├──▶ n8n Automation Engine (Private)
       ├──▶ Gitea Source Control (Private)
       ├──▶ Mermaid Diagram Service (Private)
       └──▶ Vaultwarden Admin Panel (Private / Local only)
```

---

## 🔐 Tier 1: Public Services (Cloudflare Tunnel + Hardened Nginx)

### 1. Vaultwarden (`vault.snowfox.live`)
- **Admin Panel Lockdown (`/admin`):**
  - Completely blocked from the public internet.
  - Returns `404 Not Found` to public tunnel requests.
  - Accessible ONLY from internal subnets (`10.10.10.0/24`, `192.168.1.0/24`) and Tailscale (`100.64.0.0/10`).
  - Secondary WAF block at Cloudflare Edge: URI path starts with `/admin` ➔ Action: Block.
- **Pay-to-Invite Onboarding Flow (bKash / Nagad Monetization):**
  - `SIGNUPS_ALLOWED=false` (Public registration disabled to prevent unpaid accounts).
  - `INVITATIONS_ALLOWED=true`.
  - **Registration Button Override:** In the web vault frontend or via Nginx redirect, requests to `#/register` or registration buttons redirect users to an onboarding/payment portal or Telegram Bot (`https://t.me/YourBotName?start=subscribe_vault`).
  - **Payment Verification:** User pays via bKash/Nagad and submits TrxID. Upon verification, admin approves the request, and the backend/bot triggers the Vaultwarden Admin API (`/api/admin/users/invite`) to dispatch a private tokenized invite link.
- **Security Headers:**
  - HSTS: `max-age=31536000; includeSubDomains; preload`
  - `X-Frame-Options: DENY`
  - `X-Content-Type-Options: nosniff`
  - `Referrer-Policy: strict-origin-when-cross-origin`

### 2. Public Websites & Relay
- Standard TLS termination via Cloudflare Origin CA certificate.
- WebSocket buffering enabled.

---

## 🔒 Tier 2: Private Services (Tailscale Split-DNS)

### Services:
- **n8n Workflow Engine** (`n8n.snowfox.live`)
- **Mermaid Graphing** (`mermaid.snowfox.live`)
- **Gitea Git Server** (`git.snowfox.live`)

### Ingress Mechanism:
- Cloudflare DNS record is set to **Unproxied (Gray Cloud ☁️)**:
  `n8n.snowfox.live` ➔ `100.x.y.z` (Nginx Tailscale IP).
- External internet users cannot connect (carrier-grade NAT IP is non-routable on the public internet).
- When on Tailscale (Phone or PC), WireGuard automatically resolves and connects to Nginx over the encrypted tunnel.
- Nginx terminates the connection and forwards to the private service container.

---

## 🤖 Tier 3: Telegram Bots & Automated Workflows

- **Network Placement:** Deployed in the **Not-Sure / Untrusted Zone (`vmbr3`, `10.30.30.0/24`)**.
- **Isolation Policy:** 
  - Bots communicate outward to `api.telegram.org` via long-polling (`getUpdates`).
  - Inbound firewall rejects connections from the Not-Sure Zone into the Safe Zone (`10.10.10.0/24`), protecting the core infrastructure.
  - Safe Zone services (e.g. n8n) can push updates outward to bots when required.

---

## 📋 Implementation Checklist
- [ ] Create Debian LXC container on Proxmox bridge `vmbr1` (Safe Zone IP: `10.10.10.10`).
- [ ] Install Nginx, `cloudflared`, and `tailscale`.
- [ ] Generate Cloudflare Origin CA certificate (15-year validity) and configure in Nginx.
- [ ] Update Cloudflare SSL mode from `Off` to `Full (Strict)`.
- [ ] Configure `cloudflared` to route `vault.snowfox.live` to local Nginx.
- [ ] Implement Nginx `/admin` blocking rule for Vaultwarden.
- [ ] Join container to Tailscale network.
