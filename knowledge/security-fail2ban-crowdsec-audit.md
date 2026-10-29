# 🛡️ Intrusion Prevention Audit: Fail2ban & CrowdSec Assessment

> **Date:** 2026-10-24  
> **Audited Targets:** Proxmox VE Host (`192.168.1.2`), OpenWrt VM (`192.168.1.129`), Physical Archer C6 (`192.168.1.1`)  
> **Current Status:** 🟢 **Graduated to Live** (Fail2ban deployed and active on Proxmox VE Host; see [security-fail2ban-proxmox](security-fail2ban-proxmox.md))

---

## 🔍 Initial Audit & Live Status

During initial evaluation:
- **Proxmox VE Host (`192.168.1.2`):** Evaluated and subsequently deployed with **Fail2ban** (active jails: `proxmox` Web GUI `:8006` and `sshd` `:22`). Full configuration documented in [security-fail2ban-proxmox](security-fail2ban-proxmox.md).
- **OpenWrt VM (`192.168.1.129`):** Neither `fail2ban` nor `crowdsec` is installed.
- **Physical Router (`192.168.1.1`):** Neither is installed (relies on Dropbear key-only auth and `fw4` nftables rate limiting).

---

## ⚖️ Architectural Assessment: Fail2ban vs. CrowdSec

| Feature / Metric | Fail2ban | CrowdSec |
| :--- | :--- | :--- |
| **Footprint & RAM** | ~30 MB (Python daemon) | ~80–120 MB (Go daemon + SQLite/Postgres) |
| **Mechanism** | Regex log parsing $\rightarrow$ local iptables/nftables ban | Log parsing $\rightarrow$ CAPI (Cloud API) community intelligence consensus |
| **Proxmox Suitability** | 🟢 **Excellent** (Lightweight, native Debian package, protects PVE Web UI `:8006` and SSH `:22`) | 🟡 Moderate (Higher memory overhead, requires cloud account or local bouncer) |
| **OpenWrt Suitability** | 🔴 Unsuitable (Python dependencies too heavy for 16MB flash / router RAM) | 🔴 Unsuitable (Go binary exceeds router memory constraints) |
| **OpenWrt Alternative** | **Dropbear SSH key-only auth** (`PasswordAuth 'off'`) + `nftables` connection burst rate-limiting (`hashlimit`) | Same |

---

## 📋 Recommended Action Plan

1. **For Proxmox VE Host (`192.168.1.2`):**
   - Deploy **Fail2ban** with two specific active jails:
     - `sshd` jail: Ban IP after 3 failed password/key attempts for 24 hours.
     - `proxmox` jail: Parse `/var/log/pveproxy/access.log` to ban brute-force attacks against the Proxmox Web GUI (`:8006`).
2. **For OpenWrt (Physical + VM):**
   - Enforce cryptographic boundary: disable SSH password logins (`PasswordAuth 'off'`) so brute-force dictionary attacks are impossible by design.
3. **For Vaultwarden & Public Services (`vmbr2`):**
   - Vaultwarden contains built-in rate-limiting (`ROCKET_LIMITS`).
   - Upstream Cloudflare WAF (via Cloudflare Terraform) drops malicious bot traffic and credential stuffers before they ever touch your home network.
