# 🛠️ Problems to Fix & Architectural Findings

> **Source:** Comprehensive Repository & Infrastructure Audit (`lab`)  
> **Date:** 2026-10-25  
> **Status:** Pending Review & Action  
> **Target Directory:** `~/Documents/Obsidian Vault/lab/`

---

## 📑 Table of Contents
1. [Confirmed Technical Errors & Inconsistencies](#1-confirmed-technical-errors--inconsistencies)
2. [Likely Mistakes & Architectural Ambiguities](#2-likely-mistakes--architectural-ambiguities)
3. [Operational Limitations, Capacity & Feasibility Risks](#3-operational-limitations-capacity--feasibility-risks)
4. [Prioritized Action Plan](#4-prioritized-action-plan)
5. [Open Decisions Requiring Clarification](#5-open-decisions-requiring-clarification)

---

## 1. Confirmed Technical Errors & Inconsistencies

### 1.1 Inconsistent Admin Lockdown Behavior in Vaultwarden Docs vs. Nginx Config
- **Current State:** 
  - [03-vaultwarden-service/README.md](file:///home/test/Documents/Obsidian Vault/lab/projects/03-vaultwarden-service/README.md) states that `/admin` returns an unconditional hard `404 Not Found` to public callers.
  - [cloudflare-live-status.md](file:///home/test/Documents/Obsidian Vault/lab/projects/03-vaultwarden-service/cloudflare-live-status.md) and [migration-report.md](file:///home/test/Documents/Obsidian Vault/lab/projects/03-vaultwarden-service/migration-report.md) report that it returns `403 Forbidden`.
  - In [nginx-public.conf](file:///home/test/Documents/Obsidian Vault/lab/projects/02-per-zone-nginx-proxies/nginx-public.conf), Nginx uses `deny all;` inside `location /admin`, which causes Nginx to return `403 Forbidden` by default.
- **Underlying Intent:** Conceal or strictly prevent public internet access to the `/admin` portal while allowing access exclusively from the administrator's workstation (`192.168.1.197`) or internal management tier (`10.10.10.0/24`).
- **Technical Impact:** A `403 Forbidden` response confirms to automated scanners that the `/admin` endpoint exists, whereas a `404 Not Found` provides stealth. Furthermore, the documented private `:8443` server block for admin management is missing from `nginx-public.conf`.
- **Recommended Fix:** 
  - Decide on the canonical response (`404` vs. `403`).
  - If `404` is preferred, update `nginx-public.conf`:
    ```nginx
    location /admin {
        allow 192.168.1.197;
        allow 10.10.10.0/24;
        return 404;
    }
    ```
  - Align all documentation files with the implemented behavior.

---

### 1.2 Missing `set_real_ip_from` for Cloudflare Tunnel Ingress in `nginx-public.conf`
- **Current State:** [nginx-public.conf](file:///home/test/Documents/Obsidian Vault/lab/projects/02-per-zone-nginx-proxies/nginx-public.conf) relies on IP allowlists (`allow 192.168.1.197; allow 10.10.10.0/24; deny all;`) inside the `/admin` block.
- **The Flaw:** Requests coming from the internet via the Cloudflare Tunnel daemon connect to Nginx from `127.0.0.1` (or local container IP). Without `set_real_ip_from 127.0.0.1;` and `real_ip_header CF-Connecting-IP;`, Nginx evaluates `$remote_addr` as the local tunnel client. 
- **Underlying Intent:** Ensure public visitors cannot access administrative routes while internal management endpoints can.
- **Technical Impact:** While `127.0.0.1` is blocked by `deny all;`, any internal traffic routed through reverse proxies or tunnel interfaces may be misclassified unless real IP headers are properly parsed.
- **Recommended Fix:** Explicitly configure trusted upstream tunnel proxies in Nginx:
  ```nginx
  set_real_ip_from 127.0.0.1;
  real_ip_header CF-Connecting-IP;
  ```

---

### 1.3 `power-manager.sh` WAN Revert Fails if LXC 200 Stops First
- **Current State:** In [projects/00-proxmox-host/scripts/power-manager.sh](file:///home/test/Documents/Obsidian Vault/lab/projects/00-proxmox-host/scripts/power-manager.sh), the script calls:
  ```bash
  revert_wan_mode() {
      curl -s -m 8 -X POST "http://192.168.1.130/api/set" -H "Content-Type: application/json" -d '{"mode":"1"}' >/dev/null 2>&1 || true
  }
  ```
- **The Flaw:** When Proxmox initiates a shutdown (due to battery < 40% or midnight schedule), LXC containers are stopped by systemd. If LXC 200 (`wan-controller` at `192.168.1.130`) terminates before `power-manager.sh` completes its curl call, the command fails silently (`|| true`).
- **Underlying Intent:** Ensure the physical router is guaranteed to be in Mode 1 (Physical Router Main) so the household retains internet access while the Proxmox laptop is powered down.
- **Technical Impact:** If the router was operating in Mode 2 (OpenWrt VM Main), and the curl command fails during host shutdown, the physical router remains in `network.wan.auto='0'` with `wan` down, completely cutting off home internet.
- **Recommended Fix:** Make the fallback independent of LXC 200 by having the Proxmox host execute SSH directly to the physical router:
  ```bash
  revert_wan_mode() {
      echo "Reverting router to Mode 1 directly via SSH..."
      ssh -o ConnectTimeout=3 -o BatchMode=yes root@192.168.1.1 "wan-mode 1" >/dev/null 2>&1 || true
  }
  ```

---

### 1.4 OpenWrt VM Routing Asymmetry in `wan-mode 2`
- **Current State:** In [projects/01-dual-openwrt-routing/scripts/wan-mode](file:///home/test/Documents/Obsidian Vault/lab/projects/01-dual-openwrt-routing/scripts/wan-mode), switching to Mode 2 runs `ifdown wan` and `uci set network.wan.auto='0'`. The background watchdog then checks:
  ```bash
  DEFAULT_VIA_VM=$(ip route | grep "default via 192.168.1.129" || true)
  ```
- **The Flaw:** If the static fallback route (`lan_fallback` pointing `0.0.0.0/0` to `192.168.1.129`) is not permanently active in `/etc/config/network` on the physical router, dropping `wan` leaves the physical router without any default gateway. The watchdog check fails and triggers an automatic rollback to Mode 1 after 45 seconds.
- **Underlying Intent:** Automatically route all household traffic through OpenWrt VM 100 when operating in Mode 2, with safe rollback if connectivity cannot be established.
- **Technical Impact:** Mode 2 fails safety validation and reverts prematurely.
- **Recommended Fix:** Verify and enforce that the physical router permanently retains:
  ```uci
  set network.lan_fallback=route
  set network.lan_fallback.interface='lan'
  set network.lan_fallback.target='0.0.0.0/0'
  set network.lan_fallback.gateway='192.168.1.129'
  set network.lan_fallback.metric='20'
  ```

---

## 2. Likely Mistakes & Architectural Ambiguities

### 2.1 Intra-Subnet MQTT Client Isolation vs. Routed Firewall Rules (`EXP-003`)
- **Current State:** In [EXP-003](file:///home/test/Documents/Obsidian Vault/lab/projects/01-dual-openwrt-routing/experiments/003-iot-vlan30-trunking.md), an OpenWrt firewall rule `Allow-IoT-MQTT-Mosquitto` is configured to allow `ha_iot` to reach `10.30.30.2:1883`.
- **The Issue:** Both the IoT microcontrollers (`10.30.30.10`, `10.30.30.11`) and the Mosquitto broker (`10.30.30.2`) reside on the same Layer-2 bridge (`vmbr3` / `10.30.30.0/24`). Same-subnet east-west traffic does not traverse the OpenWrt router's Layer-3 routing engine or firewall forward chains.
- **Underlying Intent:** Restrict IoT devices so they can only send telemetry to Mosquitto and cannot attack or communicate with other devices.
- **Recommended Clarification:**
  - Client isolation between wireless stations is correctly enforced by Archer C6's `option isolate '1'` on the VAP.
  - To enforce L2 isolation between Proxmox containers/VMs on the same bridge, enable Proxmox firewall (`pve-firewall` / `ebtables`) or place Mosquitto in a distinct routed subnet/bridge.

---

### 2.2 `mwan3` Subnet Range Overlap & Inter-Zone Routing
- **Current State:** In [mwan3.config.router](file:///home/test/Documents/Obsidian Vault/lab/projects/11-multiwan-load-balancing/mwan3.config.router), rule `local_subnets` excludes `192.168.1.0/24,10.0.0.0/8,172.16.0.0/12` using policy `default`.
- **The Issue:** Traffic routed to `wan_vm` uses gateway `192.168.1.129` on `br-lan`. If internal services on the physical router attempt to communicate with containers in `10.10.10.0/24` or `10.70.70.0/24`, the physical router must have explicit static routes pointing `10.0.0.0/8` to `192.168.1.129`. Otherwise, `policy 'default'` sends packets to the unrouted default interface.
- **Recommended Fix:** Ensure static routes for `10.0.0.0/8` via `192.168.1.129` are defined on the physical router:
  ```uci
  set network.route_proxmox_zones=route
  set network.route_proxmox_zones.interface='lan'
  set network.route_proxmox_zones.target='10.0.0.0/8'
  set network.route_proxmox_zones.gateway='192.168.1.129'
  ```

---

## 3. Operational Limitations, Capacity & Feasibility Risks

### 3.1 ThinkPad Hypervisor RAM Headroom (8GB RAM Cap)
- **Current Allocation:**
  - PVE Host Base: ~1.2 GiB
  - OpenWrt VM 100: 512 MiB
  - LXC 200 (`wan-controller`): 512 MiB
  - LXC 205 (`pihole-oob`): 512 MiB
  - LXC 210 (`db-central`): 2048 MiB
  - LXC 220 (`vaultwarden`): 512 MiB
  - LXC 202 (`nginx-public`): 512 MiB
  - **Total Committed:** ~5.8 GiB out of 7.6 GiB visible physical RAM.
- **Risk:** Deploying planned workloads (Immich, Gitea, Home Assistant Core, n8n, *Arr stack) on this hardware will exceed physical memory, resulting in severe swap thrashing on the 120GB SSD.
- **Mitigation:**
  1. Standardize all LXCs on Debian 13 (Trixie).
  2. Enable Kernel Samepage Merging (`ksmtuned`) on Proxmox to merge identical memory pages across containers, freeing an estimated 20%–35% RAM.
  3. Keep heavy, non-critical services (like Immich machine learning or SearXNG) running on the Main PC (`rubait`) rather than overloading the laptop server.

---

### 3.2 Dnsmasq 2.51s Latency Penalty During Nightly Proxmox Sleep
- **Observed Behavior:** From 00:00 to 07:00 AM, Proxmox powers down, taking LXC 205 (`pihole-oob` at `192.168.1.135`) offline. Because `dnsmasq` on the physical router has `strictorder '1'`, every uncached DNS query waits ~2.51 seconds for the primary socket to time out before falling back to Cloudflare for Families (`1.1.1.3`).
- **Impact:** While content filtering remains active, browsing feels sluggish for family members at night.
- **Mitigation Options:**
  - *Option A (Time-based cron):* Have the physical router cron automatically swap the primary upstream DNS to `1.1.1.3` at 00:00, and restore `192.168.1.135` at 07:05 AM.
  - *Option B (Acceptable tradeoff):* Leave as-is if off-peak nighttime latency is considered acceptable.

---

### 3.3 Physical Router SPI Flash Space vs. Project 05 & 06
- **Current State:** The TP-Link Archer C6 v3 has only 16MB SPI flash memory, with ~5.7MB free.
- **Risk:** Building Project 05 (Simple Web UI) with `uhttpd-mod-ubus`, `rpcd-mod-rpcsys`, and Project 06 (Telegram bot poller) directly on the physical router could exhaust flash memory or cause kernel buffer pressure.
- **Mitigation:**
  - Prototype and run the Telegram bot backend and complex web UIs on Proxmox LXCs or n8n workflows, keeping only lightweight ubus/API endpoints on the physical router.

---

### 3.4 ISP Dual-PPPoE Concurrency Limitation (Mode 3 Multi-WAN)
- **Feasibility Risk:** Mode 3 assumes the upstream ISP allows two concurrent PPPoE sessions over the single fiber ONU bridge. Most residential ISPs in Bangladesh bind sessions to a single MAC or reject concurrent logins on the same credentials.
- **Mitigation:** Verify whether the ISP supports multi-session login or allocate a dedicated secondary PPPoE user credential before scheduling Mode 3 production cutover.

---

## 4. Prioritized Action Plan

| Priority | Task | Affected Files / Nodes | Purpose |
| :---: | :--- | :--- | :--- |
| 🔴 **P1** | Switch `power-manager.sh` fallback to direct SSH | `projects/00-proxmox-host/scripts/power-manager.sh` | Prevent WAN lockout if LXC 200 stops before Proxmox host |
| 🔴 **P1** | Unify `/admin` lockdown response (404 vs 403) | `projects/02-per-zone-nginx-proxies/nginx-public.conf`, `projects/03-vaultwarden-service/` | Ensure stealth and remove configuration drift |
| 🔴 **P1** | Add `set_real_ip_from` for Cloudflare Tunnel | `projects/02-per-zone-nginx-proxies/nginx-public.conf` | Fix client IP detection behind `cloudflared` |
| 🟡 **P2** | Audit static fallback route on physical router | Physical Router `/etc/config/network` | Prevent 45s watchdog false-revert in Mode 2 |
| 🟡 **P2** | Enable `ksmtuned` RAM deduplication on Proxmox | Proxmox Host (`/etc/ksmtuned.conf`) | Reclaim 20%–35% memory on 8GB host |
| 🟢 **P3** | Evaluate nighttime DNS upstream cron switcher | Physical Router `/etc/crontabs/root` | Eliminate 2.5s DNS lookup timeout between 00:00–07:00 |
| 🟢 **P3** | Offload Bot Hub (Project 06/09) to Proxmox/n8n | `projects/06-openwrt-telegram-bot/`, `projects/09-telegram-bot-hub/` | Conserve 16MB SPI flash on Archer C6 |

---

## 5. Open Decisions Requiring Clarification

1. **Admin Portal Response Policy:** Should public requests to `vault.snowfox.live/admin` return a stealth `404 Not Found` (recommended) or an explicit `403 Forbidden`?
2. **Nighttime DNS Latency:** Should we implement an automated midnight cron on the router to swap primary DNS to Cloudflare Family (`1.1.1.3`) during the sleep window, or is the 2.5s fallback delay acceptable?
3. **ISP Dual-Login Status:** Does your current ISP account permit simultaneous PPPoE logins for Mode 3, or will a secondary account be required?
