# 🤖 Project 06: OpenWrt Telegram Remote Control Bot

> **Project ID:** `06-openwrt-telegram-bot`  
> **Target Device:** TP-Link Archer C6 v3 (OpenWrt 25.12.6)  
> **Source Spec:** Handoff dated 2026-10-17  
> **Core Purpose:** Out-of-home remote control and real-time monitoring of the OpenWrt router via Telegram commands and interactive inline buttons.

---

## 🎯 1. Objectives & Boundaries

### 1.1 What the Bot DOES Handle (Safe Remote Commands):
- **Status & Diagnostics:** `/status` (WAN IP, uptime, load, connected devices, pending changes).
- **Wi-Fi Controls:** `/wifi` (view settings, toggle 2.4G/5G on/off, change SSID, update password, change channels).
- **Guest Wi-Fi:** `/guest on <ssid> <pass> [duration]` (e.g., `2h`, `1d`), `/guest off`.
- **DNS Switching:** `/dns <primary> [secondary]` or `/dns auto`.
- **Physical Ethernet Ports:** `/port <1-4> on|off` (toggle LAN port data link).
- **Device Management:** `/devices` (list with inline [Block] buttons), `/name <dev> <name>`, `/block <dev> [duration]`, `/unblock <dev>`, `/limit <dev> <down> [up]`.
- **Access Policy:** `/access open|allowlist`, `/allow <mac> [name]`, `/forget <dev>`.
- **Parental Controls:** `/site <dev> deny <domain>`, `/site <dev> allow <domain>`, `/site <dev> default allow|deny`.
- **Reboot:** `/reboot [delay]`, `/reboot cancel`.
- **Pending Changes:** `/pending`, `/apply`, `/keep`, `/discard`.

### 1.2 What the Bot MUST NOT Handle (Hard Boundary):
The Telegram Bot must **NEVER** expose controls that could sever the router's internet uplink:
- ❌ **PPPoE username / password changes** (if invalid, WAN drops and the bot becomes permanently unreachable).
- ❌ **Full factory reset**
- ❌ **WAN connection type changes**
- ❌ **WAN MAC cloning**
- ❌ **Wi-Fi operational mode** (Router / Access Point / Repeater)
- ❌ **Firmware upgrading** (Bot may notify that an update is available, but the actual upgrade must be executed from the local Web UI).

---

## 🏗️ 2. Architectural Deployment Models

### Option A: Off-Router Bot on Home Server / Proxmox (Recommended for Prototype)
- Bot daemon runs on a lightweight container on Proxmox or via an **n8n Telegram workflow**.
- Communicates with the router over the secure local LAN bridge via restricted `ubus` JSON-RPC or SSH.
- Benefits: Rich Python/Node.js ecosystem, zero flash space consumed on the router, easy logging.

```
[ Telegram Cloud ]
       │
       ▼ (Long-polling / Webhook)
[ Bot Backend (Proxmox Server / n8n) ]
       │
       ▼ (LAN / Trusted Bridge: ubus / SSH)
[ Archer C6 OpenWrt Router ]
```

### Option B: Router-Native Poller (Target for Release)
- Pure shell / `ucode` daemon running directly on OpenWrt using `uclient-fetch` in a long-polling loop against `https://api.telegram.org/bot<token>/getUpdates`.
- Zero open inbound ports required; outbound HTTPS only.

---

## 🔔 3. Real-Time Security Notifications & Alerts

### 3.1 Unknown Join-Attempt Alerts (Allowlist Mode)
- Subscribes to `hostapd` ubus auth/assoc events.
- When an unregistered device attempts to associate:
  - Formats notification:
    `⚠️ Unknown device tried to join 5G · Signal -48 dBm · MAC aa:bb:cc:dd:ee:ff`
  - Inline buttons: `[ ✅ Allow ]` `[ ❌ Ignore ]`
  - Tapping **Allow** instantly registers the MAC into the allowlist!

### 3.2 Recovery & System Alerts
- **Internet Restoration Alert:** *"✅ Internet connection restored. Outage duration: 14 minutes."*
- **New Device Connected Alert.**
- **Firmware Update Notification.**

---

## 🔐 4. Bot Security & Anti-Abuse
- **User Authentication:** Strict numeric Telegram User ID allowlist (usernames are insecure as they can change).
- **Role-Based Access:** Owner (full access) vs. Limited (status view only).
- **Secret Hygiene:** When receiving sensitive data (such as Wi-Fi passwords), the bot immediately deletes the user's message from the chat history and masks the value (`••••••`) in pending change previews.
- **Destructive Confirmation:** Critical actions (like rebooting or blocking devices) require an interactive double-confirmation inline button.
