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

### 1.2 Missing `set_real_ip_from` for Cloudflare Tunnel Ingress in `nginx-public.conf` [RESOLVED]
- **Current State:** [nginx-public.conf](file:///home/test/Documents/Obsidian Vault/lab/projects/02-per-zone-nginx-proxies/nginx-public.conf) relies on IP allowlists (`allow 192.168.1.197; allow 10.10.10.0/24; deny all;`) inside the `/admin` block.
- **Resolution:** Added `set_real_ip_from 127.0.0.1;` and `real_ip_header CF-Connecting-IP;` to restore actual visitor IPs from Cloudflare Tunnel headers.

---

### 1.3 `power-manager.sh` WAN Revert Fails if LXC 200 Stops First [RESOLVED]
- **Resolution:** Updated `revert_wan_mode()` in `projects/00-proxmox-host/scripts/power-manager.sh` with a direct SSH fallback (`ssh root@192.168.1.1 "wan-mode 1"`) if the HTTP API on LXC 200 is down or stopping. Proxmox's `root@snowfox` key authorized on the physical router. Deployed to `/usr/local/bin/power-manager.sh` on Proxmox host.

---

### 1.4 OpenWrt VM Routing Asymmetry in `wan-mode 2` [RESOLVED]
- **Resolution:** Static route `lan_fallback` (`0.0.0.0/0 via 192.168.1.129 dev br-lan metric 20`) and `route_proxmox_zones` (`10.0.0.0/8 via 192.168.1.129`) are permanently committed in `/etc/config/network` on the physical router. Safe rollback watchdog operates reliably.

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

### 2.2 `mwan3` Subnet Range Overlap & Inter-Zone Routing [RESOLVED]
- **Current State:** Static route `route_proxmox_zones` (`10.0.0.0/8 via 192.168.1.129 dev br-lan`) and RFC 3442 DHCP options 121 & 249 have been committed and verified active on the physical router (`192.168.1.1`).
- **Resolution:** Home LAN devices and physical router services route directly to `10.0.0.0/8` Proxmox container tiers without being routed out `pppoe-wan`. Bidirectional forwarding on OpenWrt VM between `lan` and `safe_internal` confirmed with ~1.4ms latency.

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

| Priority | Task | Affected Files / Nodes | Purpose | Status |
| :---: | :--- | :--- | :--- | :---: |
| 🔴 **P1** | Switch `power-manager.sh` fallback to direct SSH | `projects/00-proxmox-host/scripts/power-manager.sh` | Prevent WAN lockout if LXC 200 stops before Proxmox host | 🟢 **Fixed & Deployed** |
| 🔴 **P1** | Add `set_real_ip_from` for Cloudflare Tunnel | `projects/02-per-zone-nginx-proxies/nginx-public.conf` | Fix client IP detection behind `cloudflared` | 🟢 **Fixed** |
| 🔴 **P1** | Fix WAN Controller 403 ACLs for `wan.snowfox.live` | `projects/01-dual-openwrt-routing/wan-controller/` | Enable mode switching via `https://wan.snowfox.live` | 🟢 **Fixed & Verified** |
| 🔴 **P1** | Fix Proxmox Terraform provider credentials | `iac/terraform/proxmox/` | Enable declarative LXC container management | 🟢 **Fixed & Verified** |
| 🟡 **P2** | Audit static fallback route on physical router | Physical Router `/etc/config/network` | Prevent 45s watchdog false-revert in Mode 2 | 🟢 **Verified Active** |
| 🟡 **P2** | Fix Dropbear & Pi-hole SSH authentication | `iac/inventory.py`, router, LXC 205 | Enable automated non-interactive Pyinfra execution | 🟢 **Fixed & Verified** |
| 🟡 **P2** | Enable `ksmtuned` RAM deduplication on Proxmox | Proxmox Host (`/etc/ksmtuned.conf`) | Reclaim 20%–35% memory on 8GB host | ⚪ Standby (Pending host wake) |
| 🟢 **P3** | Evaluate nighttime DNS upstream latency | Physical Router `/etc/config/dhcp` | Query measured at 57ms (no fallback penalty) | 🟢 **Audit Passed (57ms)** |
| 🟢 **P3** | Offload Bot Hub (Project 06/09) to Proxmox/n8n | `projects/06-openwrt-telegram-bot/`, `projects/09-telegram-bot-hub/` | Conserve 16MB SPI flash on Archer C6 | ⚪ Roadmap Target |

---

## 5. Open Decisions Requiring Clarification

1. **Admin Portal Response Policy:** Should public requests to `vault.snowfox.live/admin` return a stealth `404 Not Found` (recommended) or an explicit `403 Forbidden`?
2. **Nighttime DNS Latency:** Should we implement an automated midnight cron on the router to swap primary DNS to Cloudflare Family (`1.1.1.3`) during the sleep window, or is the 2.5s fallback delay acceptable?
3. **ISP Dual-Login Status:** Does your current ISP account permit simultaneous PPPoE logins for Mode 3, or will a secondary account be required?
