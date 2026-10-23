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
| **Home Assistant (IoT)**    | `vmbr3` / `eth3`   | `10.30.30.1`  | Home Assistant core, Mosquitto MQTT & IoT sensors (Tailscale) |
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
