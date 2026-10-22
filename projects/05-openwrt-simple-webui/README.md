# 🌐 Project 05: OpenWrt Simple Web UI

> **Project ID:** `05-openwrt-simple-webui`  
> **Target Device:** TP-Link Archer C6 v3 (MT7621, 16MB Flash, 128MB RAM, OpenWrt 25.12.6)  
> **Source Spec:** Handoff dated 2026-10-17  
> **Core Purpose:** A beginner-friendly, offline-capable local web dashboard hosted directly on the router that replaces LuCI for everyday users.

---

## 🎯 1. Objectives & Core Principles
- **Offline Reliability:** Must be hosted locally on the router in `/www/` via `uhttpd`. Functions even when the WAN/internet is completely down so users can fix PPPoE or Wi-Fi configuration.
- **Extreme Lightweight Footprint:** 
  - Entire frontend must be a static Single Page Application (SPA) under ~200 KB gzipped.
  - Zero heavy runtimes on the router (No Python, No Node.js).
  - Uses `ucode` / shell + `rpcd` / `ubus` for backend RPC.
- **Coexistence with LuCI:** LuCI remains available at `/cgi-bin/luci` for advanced admin tasks. The Simple UI provides a direct link: *"Advanced Settings (LuCI)"*.
- **LAN-Only Exposure:** The web UI and ubus JSON-RPC endpoints are strictly restricted to the LAN interface. Never exposed to WAN.

---

## 🏗️ 2. Architectural Design

```
+-----------------------------------------------------------+
|               Router Storage (/www/)                      |
|                                                           |
|   +---------------------------------------------------+   |
|   |         Static Single Page Web App (SPA)          |   |
|   |         (Vanilla JS / Lightweight CSS / HTML)     |   |
|   +---------------------------------------------------+   |
|                             │                             |
|                             ▼ (JSON-RPC over HTTP)        |
|                  uhttpd-mod-ubus (/ubus)                  |
|                             │                             |
+─────────────────────────────┼─────────────────────────────+
                              ▼
                 rpcd / ucode Action Dispatcher
                              │
     ┌────────────────────────┼────────────────────────┐
     ▼                        ▼                        ▼
UCI System Config       Firewall / nftables      hostapd Status
(network, wireless)     (client block/allow)     (active stations)
```

---

## 📱 3. UI Navigation & Feature Set

### 3.1 Views
1. **Home:** WAN status (Up/Down, IP), PPPoE status, 2.4G & 5G Wi-Fi overview, connected device count, quick reboot.
2. **First-Run Wizard:** Guides beginners through setting admin password, ISP connection type (PPPoE / DHCP), and Wi-Fi credentials.
3. **Internet:** Connection type (PPPoE, Static, DHCP), PPPoE username/password, DNS configuration, and WAN MAC clone.
4. **Wi-Fi Settings:**
   - 2.4 GHz & 5 GHz radios: SSID, password (masked), security mode (WPA2, WPA2/WPA3 mixed, WPA3), channel, channel width (20/40 MHz for 2.4G; 20/40/80 MHz for 5G), transmit power.
   - Guest Wi-Fi toggle with optional auto-expiry timer.
   - Wi-Fi Operation Mode (Router / Access Point / Repeater).
5. **Connected Devices & Access Control:**
   - Device row format: `[Friendly Name] - [Local IP] - [Bandwidth Limit] - [Block] [Remove]`.
   - Hostname resolution via DHCP lease parsing + persistent friendly name mapping.
   - One-click MAC-based network blocking.
   - Global Access Mode: Open (blocklist applies) vs. Allowlist Mode (only approved devices connect).
6. **Parental Controls:** Per-device domain allow/deny rules (enforced via `dnsmasq` nftset).
7. **Maintenance:** Admin password change, backup & restore archive, firmware upgrade notifications, selective config reset (Wi-Fi only, network only, or full).

---

## 🛡️ 4. Staged Changes & 60-Second Auto-Rollback Engine
To prevent users from locking themselves out when modifying Wi-Fi or network parameters:
1. Changes are queued into a **Pending Changes** bar (`N changes pending: Apply / Discard`).
2. When the user clicks **Apply**, the router creates a configuration snapshot and starts a **60-second trial timer**.
3. A banner appears: *"Keep these changes? Reverting in 45s..."*
4. If the user clicks **Keep**, the snapshot is removed and changes become permanent.
5. If connectivity is lost or the timer expires without confirmation, a background router script automatically rolls back to the snapshot and restarts network daemons.
   - **Crucial Rule:** The countdown timer runs **on the router itself**, never in client JavaScript.

---

## 📦 5. Packaging & Installation
- Installer script: POSIX `sh` compatible (`curl -fsSL ... | sh` or `uclient-fetch`).
- Pre-flight checks: Free flash space verification, board verification (`ramips/mt7621`), package manager detection (`apk` on 25.12 vs `opkg` on legacy).
- Safe backup taken before replacing `/www/index.html`.
