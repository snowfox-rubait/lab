# 🌐 Vaultwarden Cloudflare Production Live Status

> **Access URL:** [https://vault.snowfox.live](https://vault.snowfox.live)  
> **Status:** 🟢 **LIVE & PRODUCTION VERIFIED**  
> **Date Activated:** 2026-10-24  
> **Managed via IaC:** `~/.cloudflare-terraform`

---

## 🛡️ Edge Security & Geo-Fencing Enforced

1. **Bangladesh Geo-Fencing (`ip.geoip.country ne "BD"`):**
   - Implemented via Cloudflare Custom WAF Ruleset (`homelab_geo_fence` in `waf.tf`).
   - Automatically drops all traffic originating from outside Bangladesh at the Cloudflare edge before reaching your local network.
2. **Encrypted QUIC Cloudflare Tunnel:**
   - Active systemd service running in **LXC 202** (`nginx-public` on `vmbr2`).
   - All inbound traffic terminates at `nginx-public` (`10.20.20.10:80`).
3. **Application & WebSocket Reverse Proxy:**
   - Proxies traffic cleanly to **LXC 220** (`vaultwarden` at `10.20.20.11:8085`).
4. **Admin Panel Lockdown (`/admin`):**
   - Verified returning `HTTP/2 403 Forbidden` from external network. Reachable strictly from local workstation (`192.168.1.197`).
5. **Backend Database Isolation:**
   - Vaultwarden queries the 127 migrated passwords directly from the Central PostgreSQL 17 cluster in **LXC 210** (`db-central` on `vmbr7` at `10.70.70.10:5432`).
