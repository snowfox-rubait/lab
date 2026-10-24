# 📦 Vaultwarden SQLite to Central PostgreSQL Migration Plan

> **Source:** Local Docker SQLite on Workstation PC (`/home/test/vaultwarden/data/db.sqlite3`)  
> **Target:** Central PostgreSQL 17 on Proxmox LXC 210 (`vaultwarden_db` at `10.70.70.10:5432`)  
> **Source Stats:** 2 Users, 127 Vault Ciphers, Org Policies, RSA Keys

---

## 🏗️ End-to-End Ingress & Transit Architecture

```
Internet (User) 
   │
   ▼
Cloudflare Edge WAF (GeoIP Bangladesh / Anti-Bot)
   │ (Encrypted Cloudflare Tunnel)
   ▼
Physical Router (Archer C6: 192.168.1.1) 
   │ (VLAN 100 Trunk)
   ▼
OpenWrt VM (VM 100: 192.168.1.129)
   │ (Bridge vmbr2: 10.20.20.1)
   ▼
LXC 202: nginx-public (10.20.20.10)
   ├── cloudflared daemon (Ingress terminates here)
   └── Nginx reverse proxy (Applies /admin IP restrictions)
         │ (HTTP :8085)
         ▼
LXC 220: vaultwarden (10.20.20.11)
   │ (OpenWrt Firewall Pinhole: TCP 5432)
   ▼
LXC 210: db-central (10.70.70.10 on vmbr7)
   └── PostgreSQL 17 (vaultwarden_db)
```

---

## 🛠️ Step-by-Step Migration & Provisioning Sequence

### 1. Per-Zone Ingress Setup (`nginx-public` on LXC 202)
- ✅ Provisioned Debian 13 LXC 202 on `vmbr2` (`10.20.20.10/24`).
- ✅ Installed Nginx and Cloudflared.
- ✅ Deployed reverse proxy config terminating port 80/443 and proxying `/` and `/notifications/hub` to `10.20.20.11:8085`.
- ✅ Enforced `/admin` lockdown to local administrator IP (`192.168.1.197`).

### 2. Database Schema & Data Migration (`db.sqlite3` ➔ `vaultwarden_db`)
- Tooling: `pgloader` or standard Diesel migration sync.
- Steps:
  1. Dump SQLite tables with `pgloader` or Python `sqlite_to_pg.py` conversion script.
  2. Load user records, cipher hashes, organization collections, and two-factor keys into `vaultwarden_db`.
  3. Copy cryptographic keypair (`rsa_key.pem`) from `/home/test/vaultwarden/data/` into LXC 220 `/var/lib/vaultwarden/data/`.

### 3. Deploy Vaultwarden Service in LXC 220
- Deploy compiled binary or containerized lightweight runtime.
- Point `DATABASE_URL` to:
  ```env
  DATABASE_URL=postgresql://vaultwarden_user:<PASSWORD>@10.70.70.10:5432/vaultwarden_db
  ROCKET_PORT=8085
  WEBSOCKET_ENABLED=true
  SIGNUPS_ALLOWED=false
  INVITATIONS_ALLOWED=true
  ```

### 4. Cloudflare Tunnel Binding
- Bind `vault.snowfox.live` tunnel configuration to route to `http://10.20.20.10:80` (or local inside LXC 202).
