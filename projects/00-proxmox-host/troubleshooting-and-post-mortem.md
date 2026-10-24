# Troubleshooting & Post-Mortem: Proxmox Boot & Vaultwarden Outages

This runbook documents real failure scenarios, errors encountered during host power cycles and container migrations, root causes, and diagnostic commands.

---

## 1. Wake-on-LAN Latency & Boot Timing

### Symptom:
After sending the Wake-on-LAN magic packet, the hypervisor does not immediately accept SSH connections, and web services (like `https://vault.snowfox.live/`) return `502 Bad Gateway` or `Resolving timed out`.

### Root Cause:
1. **Motherboard & BIOS POST Time:** Hardware initialization on laptop hardware takes 30–45 seconds before the Linux kernel begins loading.
2. **Hypervisor Boot & Network Convergence:** Proxmox initializes physical bridge interfaces (`vmbr0`–`vmbr7`) and waits for systemd targets.
3. **VM & Container Startup Sequencing:** 
   * Virtual Machines (OpenWrt VM 100) require ~15 seconds to boot kernel and establish firewall routing.
   * Databases (`db-central` LXC 210) require PostgreSQL cluster startup and socket binding.
   * Dependent services (Vaultwarden LXC 220, Nginx LXC 202) fail or back off if their upstream gateways and databases are not ready.
4. **Expected Boot Latency:** **1 to 2 minutes** after sending the WoL packet before the hypervisor and all guests achieve steady-state network convergence.

---

## 2. Startup Sequencing & Boot Order Configuration

To prevent services from failing on boot due to missing network routes or database connectivity, Proxmox startup order and delays (`order=X,up=Y`) are enforced:

| Order | Target ID | Service Name | Type | Delay (`up`) | Purpose & Dependency |
| :---: | :---: | :--- | :---: | :---: | :--- |
| **1** | `100` | `openwrt` | VM | `15s` | **Core Router & Gateway:** Must be fully up first to route inter-bridge traffic (`vmbr2` $\leftrightarrow$ `vmbr7`) and provide DHCP/NAT. |
| **2** | `210` | `db-central` | LXC | `10s` | **Database Tier:** Starts PostgreSQL 17 and Redis so databases are listening before application containers start. |
| **3** | `220` | `vaultwarden` | LXC | `5s` | **Core Application:** Connects to PostgreSQL over `vmbr7` pinhole. Starts before reverse proxy. |
| **4** | `202` | `nginx-public` | LXC | `5s` | **Public Ingress:** Starts Nginx and `cloudflared` tunnel daemon to expose services externally. |
| **5** | `205` | `pihole-oob` | LXC | `0s` | **DNS Sinkhole:** Starts out-of-band DNS service on `vmbr0`. |
| **6** | `200` | `wan-controller`| LXC | `0s` | **Controller Scripts:** General background utilities. |

---

## 3. Historical Errors, Root Causes & Fixes

### Issue A: `relation "users" already exists` (Vaultwarden Crash)
* **Error:** Diesel database migration panics on startup, entering a crash loop.
* **Root Cause:** Schema migration tools like `pgloader` pre-created database tables without registering Diesel's migration metadata table `__diesel_schema_migrations`.
* **Fix:** Wipe the database, allow Vaultwarden to initialize cleanly against an empty database to run native Diesel migrations, then copy data rows using Python with `session_replication_role = 'replica'` to bypass foreign key constraint ordering.

### Issue B: `column "enabled" is of type boolean but expression is of type integer`
* **Error:** PostgreSQL rejects SQLite row inserts during migration.
* **Root Cause:** SQLite stores booleans as `0` or `1`. PostgreSQL 17 enforces strict type safety and refuses implicit integer-to-boolean coercion.
* **Fix:** Query PostgreSQL `information_schema.columns` to dynamically detect all boolean columns, casting integer values to Python `bool()` before insertion.

### Issue C: Browser Subtle Crypto API Insecure Context Error
* **Error:** Web browser blocks Bitwarden/Vaultwarden web vault logins with: *"You are not using a secure context which is required for the Subtle Crypto API to work."*
* **Root Cause:** Cloudflare Tunnel terminates SSL at the edge, but Nginx upstream was not passing HTTPS headers, making the browser treat the payload as plaintext HTTP.
* **Fix:** In Nginx reverse proxy (`nginx-public` / LXC 202):
  ```nginx
  proxy_set_header X-Forwarded-Proto https;
  proxy_set_header X-Forwarded-Ssl on;
  ```

### Issue D: `FATAL: no pg_hba.conf entry for host "10.70.70.1"` (502 Bad Gateway)
* **Error:** Vaultwarden fails to start after reboot; Cloudflare returns `502 Bad Gateway`. Vaultwarden logs show `Can't connect to database: DieselCon`.
* **Root Cause:** When Vaultwarden (`10.20.20.11`) routes through the OpenWrt VM gateway into `vmbr7`, the OpenWrt firewall masquerades the traffic with source IP `10.70.70.1`. PostgreSQL's `pg_hba.conf` was locked down to only allow `10.20.20.11/32`.
* **Fix:** Update `/etc/postgresql/17/main/pg_hba.conf` on `db-central` (LXC 210) to permit the database subnet gateway:
  ```text
  hostssl vaultwarden_db vaultwarden_user 10.70.70.0/24 scram-sha-256
  ```

### Issue E: OpenWrt VM Interface Mismatch (`eth5` vs `eth6`)
* **Error:** Destination host unreachable when pinging `10.70.70.10` from OpenWrt VM after cold boot.
* **Root Cause:** Proxmox assigned `net5` (`vmbr7`) to VM 100, which Linux enumerated as `eth5`, while UCI network config had previously referenced hotplugged `eth6`.
* **Fix:** Ensure `/etc/config/network` on OpenWrt VM permanently binds interface `database` to `eth5`:
  ```uci
  set network.database.device='eth5'
  commit network
  ```

---

## 4. Quick Diagnostic Commands

```bash
# 1. Wake Proxmox Host from Workstation
wake-proxmox

# 2. Check Proxmox & Container Status
ssh proxmox "uptime; pct list; qm list"

# 3. Check Live Public Vaultwarden Endpoint
curl -I https://vault.snowfox.live/

# 4. Inspect Vaultwarden Application Logs
ssh proxmox "pct exec 220 -- docker logs --tail 25 vaultwarden"

# 5. Check Cloudflare Tunnel Health
ssh proxmox "pct exec 202 -- systemctl status cloudflared"

# 6. Verify Database Connectivity from Container
ssh proxmox "pct exec 220 -- nc -zv 10.70.70.10 5432"
```
