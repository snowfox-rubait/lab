# 🧰 Inventory & Environment Manifest

> **Purpose:** Master registry of all physical hardware, network endpoints, credentials, domain assets, and tooling available in the homelab and workbench. Reference this whenever designing solutions, debugging, or planning architecture.

---

## 🖥️ Compute & Host Nodes

| Asset Name | Role / Function | Hardware / Platform | Access Command / Details |
| :--- | :--- | :--- | :--- |
| **Main PC** | Primary Workstation / Host | HP EliteDesk 800 G3 Mini | Local host (`rubait`) |
| **Proxmox Host** | Hypervisor Server | ThinkPad Laptop (Intel i5 3rd Gen) | `ssh proxmox` (`192.168.1.2`) |
| **Physical Router** | Main Home Gateway & Wi-Fi AP | TP-Link Archer C6 v3 (OpenWrt) | `ssh router` (`192.168.1.1`) |
| **Mobile Node** | Mobile Companion / Automations | Realme P1 5G (Termux + MacroDroid) | `ssh phone` |
| **Virtual Router** | Test lab & Container Gateway | OpenWrt 25.12.6 VM (Proxmox VM 100) | `ssh openwrt-vm` (`192.168.1.129`) |

---

## 🔌 Hardware Workbench & Microcontrollers

- **ESP32 Dev Boards** (Wi-Fi + BLE IoT prototyping)
- **ESP8266 Dev Boards** (Wi-Fi low-cost IoT nodes)
- **Arduino Uno** (Microcontroller experimentation)
- **USB Video Capture Card** (Video ingest / streaming / monitoring)
- **HDMI Splitter** (Display signal duplicating)
- **USB-to-Ethernet Adapter** (`35b5:3500` Naxiang SZNX LAN 100M - Swing WAN for Proxmox OpenWrt)

---

## 🌐 Accounts, Identity & Web Assets

- **GitHub Profile:** `snowfox-rubait`
  - Authentication: `git` and `gh` CLI fully authenticated locally.
- **Apex Domain:** `snowfox.live`
  - **Registrar / Expiry:** Registered 2026-03-17, Expires **2027-03-17** (~147 days remaining).
  - **DNS & Edge:** Cloudflare Zone ID `bf2fea1c489c7d7d258011e77305d30b`, Account ID `cd241dca8e1b54b75d761bf0225ceea4`.
  - **IaC Tooling:** Terraform in `~/.cloudflare-terraform/` (Tunnel `snowfox-tunnel` ID: `c63f3937-1ec8-4d41-9a7b-f7cc99d37efd`).
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

| Zone / Subnet | VLAN / Bridge | Gateway IP | Intended Purpose |
| :--- | :--- | :--- | :--- |
| **Home LAN** | `vmbr0` / `br-lan` | `192.168.1.1` | Wi-Fi devices, PC, Proxmox host management |
| **Safe (DMZ)** | `vmbr1` / `eth1` | `10.10.10.1` | n8n, Vaultwarden, Nginx, MQTT, Telegram Bots |
| **Unsafe (Lab)** | `vmbr2` / `eth2` | `10.20.20.1` | Malware analysis, untrusted experiments (isolated) |
| **Not-Sure (Test)**| `vmbr3` / `eth3` | `10.30.30.1` | Temporary staging and proof-of-concepts |

---

## 🖧 Hardware MAC Addresses & WOL Reference

| Device / Interface | MAC Address | IP Mapping | Notes |
| :--- | :--- | :--- | :--- |
| **Proxmox Laptop (Built-in LAN `enp12s0`)** | `b8:88:e3:e7:5e:1f` | `192.168.1.2` | Primary Wake-on-LAN target |
| **Proxmox Legacy Static Lease (`eno1`)** | `10:62:e5:00:9f:8f` | `192.168.1.2` | Configured in router `/etc/config/dhcp` |
| **Proxmox USB Adapter (`eth4`)** | `ec:9a:0c:1c:c3:dd` | Dynamic / WAN | USB-Ethernet swing WAN |
| **ThinkPad Wi-Fi (`wlp3s0`)** | `60:36:dd:50:c6:8e` | `192.168.1.153` | Internal wireless card |
| **Main Workstation PC** | `94:b8:6d:59:b8:6b` | `192.168.1.197` | HP EliteDesk Mini PC |
