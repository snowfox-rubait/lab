# 🧰 Inventory & Environment Manifest

> **Purpose:** Master registry of all physical hardware, network endpoints, credentials, domain assets, and tooling available in the homelab and workbench. Reference this whenever designing solutions, debugging, or planning architecture.

---

## 🖥️ Compute & Host Nodes

| Asset Name          | Role / Function                | Hardware / Platform                 | Access Command / Details           |
| :------------------ | :----------------------------- | :---------------------------------- | :--------------------------------- |
| **Main PC**         | Primary Workstation / Host     | HP EliteDesk 800 G3 Mini            | Local host (`rubait`)              |
| **Proxmox Host**    | Hypervisor Server              | ThinkPad Laptop (Intel i5 3rd Gen)  | `ssh proxmox` (`192.168.1.2`)      |
| **Physical Router** | Main Home Gateway & Wi-Fi AP   | TP-Link Archer C6 v3 (OpenWrt)      | `ssh router` (`192.168.1.1`)       |
| **Mobile Node**     | Mobile Companion / Automations | Realme P1 5G (Termux + MacroDroid)  | `ssh phone`                        |
| **Virtual Router**  | Test lab & Container Gateway   | OpenWrt 25.12.6 VM (Proxmox VM 100) | `ssh openwrt-vm` (`192.168.1.129`) |

---

## 🔌 Hardware Workbench & Microcontrollers

- **ESP32 Dev Boards** (Wi-Fi + BLE IoT prototyping - MAC tracked in `.env`)
- **ESP8266 Dev Boards** (Wi-Fi low-cost IoT nodes - MAC tracked in `.env`)
- **Arduino Uno** (Microcontroller experimentation)
- **USB Video Capture Card** (Video ingest / streaming / monitoring)
- **HDMI Splitter** (Display signal duplicating)
- **USB-to-Ethernet Adapter** (`35b5:3500` Naxiang SZNX LAN 100M - Swing WAN for Proxmox OpenWrt)

---

## 🌐 Accounts, Identity & Web Assets

- **GitHub Profile:** `snowfox-rubait`
  - Authentication: `git` and `gh` CLI fully authenticated locally.
- **Apex Domain:** `snowfox.live`
  - **Registrar / Expiry:** Registered 2026-03-17, Expires **2027-03-17**.
  - **DNS & Edge:** Cloudflare (Zone ID, Account ID, Tunnel ID configured via local `.env`).
  - **IaC Tooling:** Terraform in `~/.cloudflare-terraform/` (`snowfox-tunnel`).
  - **Current Live DNS Records:** None (Clean slate; old ZeroTier `openwrt` and idle tunnel CNAMEs destroyed via Terraform).
  - **Cloudflare Security Posture:**
    - Security Level: `Medium`
    - TLS 1.3: `Enabled`
    - Current SSL Mode: `Off` *(Action item: Set to `Full (Strict)` once Nginx Cloudflare Origin CA certificate is mounted)*.
- **Cloud Database Providers:**
  - Supabase (PostgreSQL / Auth / Storage)
  - Neon (Serverless Postgres)
  - *Strategy:* Cloud DBs for high-availability 24/7 services, paired with local cold-backup sync containers on Proxmox.

---

## 🐳 Running PC Services (Local Docker)

The HP EliteDesk Mini PC currently runs several local services:
- **SearXNG** (Decentralized privacy search engine - recommended per-host)
- **Ollama** (Local LLMs / AI runtime)
- **n8n** (Workflow automations)
- **Vaultwarden** (Password manager)

---

## 🗺️ Network Zones Topology

| Zone / Subnet               | VLAN / Bridge      | Gateway IP    | Intended Purpose                                              |
| :-------------------------- | :----------------- | :------------ | :------------------------------------------------------------ |
| **Home LAN / OOB**          | `vmbr0` / `br-lan` | `192.168.1.1` | Wi-Fi devices, PC, Proxmox host management, LXC 200, Pi-hole  |
| **Safe (Internal)**         | `vmbr1` / `eth1`   | `10.10.10.1`  | Central DB, DBBackup, Gitea, Immich, NAS, n8n, BookStack      |
| **Safe (Public Ingress)**   | `vmbr2` / `eth2`   | `10.20.20.1`  | Vaultwarden, Headscale (via Cloudflare Tunnel)                |
| **Home Assistant (IoT)**    | `vmbr3` / `eth3`   | `10.30.30.1`  | Home Assistant core, Mosquitto MQTT & IoT sensors (VLAN 30 / Tailscale) |
| **Unsafe (Online / Lab)**   | `vmbr4` / `eth4`   | `10.40.40.1`  | Tor obfs4, *Arr stack, qBittorrent (storage via host mount)   |
| **DMZ (Direct Ingress)**    | `vmbr5` / `eth5`   | `10.50.50.1`  | Asterisk/FreePBX VoIP, Self-Hosted Mail (Fail2ban, raw ports) |
| **Management Bots**         | `vmbr6` / `eth6`   | `10.60.60.1`  | Isolated Telegram & automation bots with audited pinholes     |

---

## 🖧 Hardware MAC Addresses & WOL Reference

> **Note:** Exact hardware MAC addresses are maintained in the local gitignored `.env` file (see `.env.example`).

| Device / Interface | Variable in `.env` | IP Mapping | Notes |
| :--- | :--- | :--- | :--- |
| **Proxmox Laptop (Built-in LAN `enp12s0`)** | `MAC_PROXMOX_BUILTIN` | `192.168.1.2` | Primary Wake-on-LAN target |
| **Proxmox Legacy Lease (`eno1`)** | `MAC_PROXMOX_LEGACY` | `192.168.1.2` | Former static lease in `/etc/config/dhcp` |
| **Proxmox USB Adapter (`eth4`)** | `MAC_PROXMOX_USB` | Dynamic / WAN | USB-Ethernet swing WAN |
| **ThinkPad Wi-Fi (`wlp3s0`)** | `MAC_PROXMOX_WIFI` | `192.168.1.153` | Internal wireless card (standby) |
| **Main Workstation PC** | `MAC_MAIN_PC` | `192.168.1.197` | HP EliteDesk Mini PC |
| **OpenWrt VM (VM 100 `eth0`)** | `MAC_OPENWRT_VM` | `192.168.1.129` | Virtual Core Router LAN Interface |
| **WAN Controller (LXC 200 `eth0`)** | `MAC_LXC_WAN_CONTROLLER` | `192.168.1.130` | Fail-safe Out-of-Band Dashboard |
| **ESP32 Dev Board** | `MAC_ESP32` | `10.30.30.10` / Dynamic | IoT Sensor / ESPHome Node (VLAN 30) |
| **ESP8266 Dev Board** | `MAC_ESP8266` | `10.30.30.11` / Dynamic | IoT Sensor Node (VLAN 30) |

---

## 🚦 Active Deployment & Service State Matrix

> **Note for Any Agent / Auditor:** This matrix distinguishes what is **actively running right now** versus what is an **architectural target / planned phase**.

| Service / Node | Platform | Network Location | Status | Current Details / Source Files |
| :--- | :--- | :--- | :--- | :--- |
| **Physical Gateway** | TP-Link Archer C6 v3 | `192.168.1.1` (LAN) | 🟢 **Live** | Mode 1 PPPoE, `wan-mode` script (`projects/01/scripts/wan-mode`), cron auto-reboot & 07:00 WOL |
| **Proxmox Hypervisor** | ThinkPad Laptop | `192.168.1.2` (`vmbr0`) | 🟢 **Live** | PVE 9.2.2, kernel 7.0, `power-manager.sh` (`projects/00/scripts/power-manager.sh`), `wol.service` |
| **Virtual Router (VM 100)** | OpenWrt 25.12.6 VM | `192.168.1.129` (`vmbr0`) | 🟢 **Live** | Standby `wan_vlan` (VLAN 100), gateway for `safe_internal`, `public_ingress`, and `ha_iot` zones |
| **WAN Controller (LXC 200)**| Debian 12 LXC | `192.168.1.130` (`vmbr0`) | 🟢 **Live** | Nginx + Python API (`projects/01/wan-controller/app.py`), Web dashboard on port 80 |
| **Local Mini PC Services** | Docker on HP EliteDesk | `192.168.1.197` (LAN) | 🟢 **Live** | SearXNG, Ollama LLM, n8n, local Vaultwarden container |
| **IoT Wi-Fi (VLAN 30)** | Archer C6 `radio0` | `10.30.30.0/24` (`vmbr3`) | 🟡 **Ready** | Specification complete (`EXP-003`). Ready to deploy upon entering hardware MACs. |
| **Reverse Proxies (LXC 201/202)**| Proxmox LXC | `vmbr1` / `vmbr2` | ⚪ **Planned** | Phase 2 target (`projects/02-per-zone-nginx-proxies`) |
| **Vaultwarden Migration** | Proxmox LXC | `10.20.20.11` (`vmbr2`) | ⚪ **Planned** | Phase 3 target (`projects/03-vaultwarden-service`), replacing PC Docker instance |
| **Central Database (PG/Redis)** | Proxmox LXC | `10.10.10.x` (`vmbr1`) | ⚪ **Planned** | Planned multi-tenant database for Gitea, Immich, Vaultwarden |
| **Home Assistant Core** | Proxmox VM / LXC | `10.30.30.x` (`vmbr3`) | ⚪ **Planned** | Planned smart home hub with native Tailscale |
| **Mosquitto MQTT Broker** | Proxmox LXC | `10.30.30.10` (`vmbr3`) | ⚪ **Planned** | Planned broker for ESP32/ESP8266 telemetry (`EXP-003`) |
| **Management Bots (LXC)** | Proxmox LXC | `10.60.60.10` (`vmbr6`) | ⚪ **Planned** | Planned isolated bot container with forced-command SSH wrapper |

---

## 🔑 SSH Client Configuration Reference

To replicate the management workstation's direct host access from any environment, configure `~/.ssh/config` as follows:

```sshconfig
Host proxmox
    HostName 192.168.1.2
    User root
    Port 22
    IdentityFile ~/.ssh/id_rsa_gemini_codeberg

Host router
    HostName 192.168.1.1
    User root
    Port 22

Host openwrt-vm
    HostName 192.168.1.129
    User root
    Port 22
    IdentityFile ~/.ssh/id_rsa_gemini_codeberg

Host phone
    HostName 192.168.1.179
    User u0_a344
    Port 8022

Host laptop
    HostName 192.168.1.153
    User haw
    Port 22
    IdentityFile ~/.ssh/id_rsa_gemini_codeberg
```

---

## 🔄 OpenWrt VM Interface & Network Zone Mapping

The OpenWrt VM (VM 100) interfaces are unified with the master architecture zones:

| UCI Interface Name | Linux Device | Proxmox Bridge | Gateway Subnet | Architectural Role | Current Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `network.homelan` | `eth0` | `vmbr0` | `192.168.1.129/24` | Out-of-Band Management & Physical LAN link | 🟢 Live |
| `network.safe_internal` | `eth1` | `vmbr1` | `10.10.10.1/24` | Safe Internal Zone (DB, NAS, Gitea) | 🟢 Live |
| `network.public_ingress`| `eth2` | `vmbr2` | `10.20.20.1/24` | Safe Public Ingress (Tunnel, Vaultwarden) | 🟢 Live |
| `network.ha_iot` | `eth3` | `vmbr3` | `10.30.30.1/24` | Home Assistant & IoT Zone (VLAN 30 Trunk) | 🟢 Live |
| `network.wan_fiber` | `eth4` | USB Passthrough | Dynamic PPPoE | Direct Fiber WAN (Emergency swing link) | 🟢 Live (Metric 15) |
| `network.wan_vlan` | `eth5` | `vmbr100` | Dynamic PPPoE | VLAN 100 Tagged PPPoE Dialer (Mode 2 / Mode 3) | 🟢 Live (Metric 10) |
| `network.unsafe` | *Pending* | `vmbr4` | `10.40.40.1/24` | Unsafe Online (Tor, *Arr, qBittorrent) | ⚪ Bridge Created on Host |
| `network.dmz` | *Pending* | `vmbr5` | `10.50.50.1/24` | Direct Ingress DMZ (Asterisk, Mail) | ⚪ Bridge Created on Host |
| `network.mgmt_bots` | *Pending* | `vmbr6` | `10.60.60.1/24` | Management Bots Zone (Telegram) | ⚪ Bridge Created on Host |
