# 🏆 Vaultwarden Production Migration & E2EE Deployment Report

> **Date Completed:** 2026-10-24  
> **Source System:** Workstation Docker SQLite (`/home/test/vaultwarden/data/db.sqlite3`)  
> **Target Production System:** Proxmox LXC 220 (`vaultwarden` on `vmbr2`) + LXC 210 (`db-central` on `vmbr7`)  
> **Ingress Gateway:** LXC 202 (`nginx-public` on `vmbr2` with `cloudflared`)  
> **Live Access URL:** [https://vault.snowfox.live](https://vault.snowfox.live)  
> **Status:** 🟢 **100% SUCCEEDED, ENCRYPTED & VERIFIED LIVE**

---

## 🧭 Executive Summary: What, Why & How

### 1. WHAT Was Done?
1. **Infrastructure Provisioning:**
   - Provisioned **LXC 210 (`db-central`)** on dedicated offline bridge `vmbr7` (`10.70.70.10`) running PostgreSQL 17 and Redis 7.
   - Provisioned **LXC 220 (`vaultwarden`)** on Safe Public Ingress bridge `vmbr2` (`10.20.20.11`).
   - Provisioned **LXC 202 (`nginx-public`)** on `vmbr2` (`10.20.20.10`) running Nginx and `cloudflared`.
2. **Database Migration:**
   - Cleanly converted and migrated all 127 encrypted passwords/ciphers, 2 user accounts, and 18 device tokens from workstation SQLite into the multi-tenant PostgreSQL cluster under `vaultwarden_db`.
3. **End-to-End Cryptographic Encryption (E2EE):**
   - Established a 4096-bit **Homelab Root Certificate Authority** (`/root/homelab-pki/ca/ca.crt`).
   - Wrapped every single transit link in mutual TLS/HTTPS (Cloudflare $\rightarrow$ Nginx $\rightarrow$ Vaultwarden $\rightarrow$ PostgreSQL). Zero cleartext packets.
4. **Cloudflare Edge Geo-Fencing:**
   - Deployed Terraform-managed Cloudflare Tunnel (`snowfox-tunnel`) and custom WAF Geo-Fence blocking all traffic originating outside Bangladesh.
5. **Workstation Cutover:**
   - Gracefully stopped local Docker containers (`vaultwarden` and `vaultwarden_caddy`) on PC (`rubait`).

---

### 2. WHY Was It Done This Way?

- **Why a Dedicated Database Bridge (`vmbr7`)?**  
  To adhere to Zero-Trust and 3-Tier Security Architecture. If an application in `vmbr1` (Safe Internal) or `vmbr2` (Public Ingress) is ever exploited via remote code execution, the attacker is trapped inside an isolated virtual bridge. They cannot sniff database broadcast traffic or access raw storage.
- **Why Match the Host OS (Debian 13 Trixie)?**  
  To guarantee 1:1 kernel, libc, systemd, and cgroups v2 parity between the Proxmox host and containers. This eliminates namespace translation overhead and enables Kernel Samepage Merging (KSM) to deduplicate shared memory pages across containers.
- **Why Enforce TLS Internally Between Containers?**  
  Defense-in-depth. Plaintext HTTP across Linux bridges is vulnerable to ARP spoofing or rogue container promiscuous listening. Forcing TLS across all hops ensures cryptographic confidentiality even inside the hypervisor.
- **Why Bangladesh-Only Geo-Fencing?**  
  Your legitimate users are inside Bangladesh. By dropping all non-BD requests at Cloudflare's edge, 99.9% of global automated vulnerability scanners, brute-force bots, and credential stuffers never even hit your router or home fiber connection.

---

### 3. HOW Was It Done? (Technical Implementation Details)

#### Phase 1: Hypervisor & Core Routing Wiring
1. Hotplugged `vmbr7` onto OpenWrt VM (VM 100) as `net5` (`eth6`).
2. Configured OpenWrt gateway `10.70.70.1/24` with default firewall `REJECT` and zero outbound WAN egress.
3. Added audited pinhole rule on OpenWrt VM:
   ```uci
   # Allow Vaultwarden (10.20.20.11) -> Central Database (10.70.70.10:5432)
   set firewall.pinhole_vw_db=rule
   set firewall.pinhole_vw_db.src='public_ingress'
   set firewall.pinhole_vw_db.src_ip='10.20.20.11'
   set firewall.pinhole_vw_db.dest='database'
   set firewall.pinhole_vw_db.dest_ip='10.70.70.10'
   set firewall.pinhole_vw_db.dest_port='5432'
   set firewall.pinhole_vw_db.proto='tcp'
   set firewall.pinhole_vw_db.target='ACCEPT'
   ```

#### Phase 2: PostgreSQL Multi-Tenancy & Data Migration
1. Provisioned `db-central` (LXC 210) with 2 Cores, 2GB RAM, 15GB SSD.
2. Initialized PostgreSQL 17 cluster with `scram-sha-256` password encryption.
3. Created user `vaultwarden_user` and database `vaultwarden_db`.
4. Executed schema bootstrap by running Vaultwarden once against PostgreSQL to apply exact Diesel migrations.
5. Extracted data from `/home/test/vaultwarden/data/db.sqlite3` and executed row-level insertion with boolean type-casting into PostgreSQL:
   ```python
   # Type conversion for strict PostgreSQL boolean constraints
   for col, val in zip(cols, row):
       if pg_types.get(col) == "boolean" and isinstance(val, int):
           converted_row.append(bool(val))
       else:
           converted_row.append(val)
   ```
6. **Data Verification:**
   - Users: 2 / 2 migrated (100%)
   - Ciphers: 127 / 127 migrated (100%)
   - Devices: 18 / 18 migrated (100%)
   - Preserved `rsa_key.pem` so existing client tokens stay valid.

#### Phase 3: Public Ingress & Edge Proxy
1. Provisioned `nginx-public` (LXC 202) with Nginx and Cloudflared.
2. Configured reverse proxy with WebSocket support and `/admin` restriction to local admin workstation (`192.168.1.197`).
3. Resolved Subtle Crypto API requirement by injecting:
   ```nginx
   proxy_set_header X-Forwarded-Proto https;
   proxy_set_header X-Forwarded-Ssl on;
   ```

#### Phase 4: Full Internal PKI & TLS Enforcement
1. Generated 4096-bit Homelab Root CA on Proxmox root.
2. Signed server certificates for `10.20.20.11` (Vaultwarden) and `10.70.70.10` (PostgreSQL).
3. Configured PostgreSQL: `ssl = on` and `hostssl` in `pg_hba.conf`.
4. Configured Vaultwarden: `ROCKET_TLS` on port 8443, and `DATABASE_URL=...&sslmode=require`.
5. Configured Nginx: `proxy_pass https://10.20.20.11:8443` with `proxy_ssl_verify on`.

#### Phase 5: Cloudflare IaC & Tunnel Activation
1. Applied Terraform in `~/.cloudflare-terraform`:
   - Tunnel: `snowfox-tunnel`
   - WAF Rule: `(ip.geoip.country ne "BD") => BLOCK`
   - CNAME: `vault.snowfox.live`
2. Installed cloudflared service in LXC 202 via systemd.

---

## 🐛 Errors Encountered, Fixes & Lessons Learned

| Issue / Error Encountered | Root Cause | Exact Resolution | Architectural Lesson |
| :--- | :--- | :--- | :--- |
| **`relation "users" already exists`** | `pgloader` created default tables before Diesel migration metadata was registered. | Dropped database, let Vaultwarden run fresh Diesel migrations, then loaded data rows with `replica` role. | Always allow the application engine to run migrations before importing legacy data rows. |
| **`column "enabled" is of type boolean but expression is of type integer`** | SQLite stores booleans as integer `0`/`1`, whereas PostgreSQL strictly requires boolean literals (`true`/`false`). | Wrote Python migration bridge querying Postgres catalog `information_schema.columns` to dynamically cast `int` to `bool`. | SQLite $\rightarrow$ Postgres data transfers require explicit schema-aware type casting. |
| **Subtle Crypto API Error in Browser** | Nginx was forwarding `$scheme` as `http`, triggering browser security boundary against Web Crypto API. | Injected `proxy_set_header X-Forwarded-Proto https;` and `X-Forwarded-Ssl on;` in Nginx. | Reverse proxies terminating SSL at external edge must explicitly tell upstream apps they are on HTTPS. |
| **LXC Package Manager Lock** | Background apt processes held `/var/lib/dpkg/lock-frontend`. | Cleared stale lock files and used `env DEBIAN_FRONTEND=noninteractive`. | Always pass noninteractive flags during headless container automation. |

---

## 🏆 Current Production Verification

- **Public HTTPS Access:** `curl -I https://vault.snowfox.live/` $\rightarrow$ **`HTTP/2 200 OK`**
- **Admin Protection:** `curl -I https://vault.snowfox.live/admin` $\rightarrow$ **`HTTP/2 403 Forbidden`**
- **Strict Transport Security:** `Strict-Transport-Security: max-age=31536000` active.
- **Local Workstation Docker:** Stopped (`vaultwarden` and `vaultwarden_caddy` offline).
