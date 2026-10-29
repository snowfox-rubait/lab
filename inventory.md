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
| **Virtual Router**        | Test lab & Container Gateway        | OpenWrt 25.12.6 VM (Proxmox VM 100) | `ssh openwrt-vm` (`192.168.1.129`) |
| **Pi-hole DNS Sinkhole**  | Out-of-Band Adblock & Parental Sink | Debian 12 LXC (Proxmox LXC 205)     | Web UI: `http://192.168.1.135/admin` (`projects/07-pihole-dns-sinkhole`) |
| **n8n Automation Engine** | Low-Code Event & Breach Watchdog   | Proxmox LXC (Planned - `vmbr1`)     | Web UI: `http://10.10.10.25:5678` (`projects/08-n8n-workflow-automation`) |
| **Telegram Bot Hub**      | Central Alerting & Dispatcher       | Node/Python daemon (Planned)        | Bot API (`projects/09-telegram-bot-hub`) |

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
| **Home LAN / OOB**          | `vmbr0` / `eth0`   | `192.168.1.1` | Wi-Fi devices, PC, Proxmox host management, LXC 200, Pi-hole  |
| **Safe (Internal Apps)**    | `vmbr1` / `eth1`   | `10.10.10.1`  | Private internal apps: Gitea, Immich, NAS, n8n, BookStack, Kiwix, Stirling-PDF, IT-Tools |
| **Safe (Public Ingress)**   | `vmbr2` / `eth2`   | `10.20.20.1`  | Vaultwarden (`10.20.20.11`), Nginx Public (`10.20.20.10`) with Cloudflare Tunnel (Headscale decoupled/undecided) |
| **Home Assistant (IoT)**    | `vmbr3` / `eth3`   | `10.30.30.1`  | Home Assistant core, Mosquitto MQTT & IoT sensors (VLAN 30 / Tailscale) |
| **Unsafe (Online / Lab)**   | `vmbr4` *(Planned)*| `10.40.40.1`  | *Arr stack, qBittorrent (storage via host mount)              |
| **DMZ (Direct Ingress)**    | `vmbr5` *(Planned)*| `10.50.50.1`  | Asterisk/FreePBX VoIP, Self-Hosted Mail (Fail2ban, raw ports) |
| **Management Bots**         | `vmbr6` *(Planned)*| `10.60.60.1`  | Isolated Telegram & automation bots with audited pinholes     |
| **Database (Data Tier)**    | `vmbr7` / `eth5`   | `10.70.70.1`  | Central Multi-Tenant DB (`10.70.70.10`: PostgreSQL 17, Redis 7), DBBackup sync |

---

## 🌐 Authoritative Internal Unicast DNS Hierarchy (`.lab`)

> **Architectural Standard:** Established in [ADR-007](knowledge/architecture-decisions.md#adr-007-authoritative-internal-unicast-dns-lab-hierarchy-vs-multicast-dns-mdns-in-segmented-zero-trust-architecture). To ensure clean resolution across isolated Layer-3 bridges without leaking broadcast discovery or violating zero-trust boundaries (avoiding mDNS), internal nodes are mapped via Unicast DNS (`dnsmasq` on OpenWrt and Pi-hole) under `.lab`:

| Node / Service | Primary IP | Canonical FQDN | Bridge / Network Zone | Role / Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Physical Gateway** | `192.168.1.1` | `router.lab` | `vmbr0` (Home LAN) | Physical Archer C6 Gateway & DHCP |
| **Proxmox Hypervisor** | `192.168.1.2` | `proxmox.lab` | `vmbr0` (Management) | PVE Web GUI (:8006) & Host SSH |
| **WAN Controller** | `192.168.1.130`| `wan.lab` | `vmbr0` (OOB WebUI) | Fail-Safe WAN Mode Dashboard (:80) |
| **Pi-hole Sinkhole** | `192.168.1.135`| `pihole.lab` | `vmbr0` (DNS OOB) | Out-of-Band Ad & Adult DNS Filter |
| **Main Workstation** | `192.168.1.197`| `workstation.lab` | `vmbr0` (Admin LAN) | Management PC / Ollama / SearXNG |
| **Virtual Core Router** | `192.168.1.129`| `vm-router.lab` | Multi-Bridge Core | OpenWrt VM (VM 100) Core Router |
| **Public Reverse Proxy** | `10.20.20.10` | `ingress.lab` | `vmbr2` (Public Ingress) | Nginx Public Ingress (`nginx-public`) |
| **Vaultwarden Vault** | `10.20.20.11` | `vaultwarden.lab`| `vmbr2` (Public Ingress) | Encrypted Bitwarden Vault (:8443) |
| **Central Database** | `10.70.70.10` | `db.lab` | `vmbr7` (Database Tier) | Multi-tenant PostgreSQL 17 & Redis 7 |
| **Database Backup Sync** | `10.70.70.11` | `dbbackup.lab` | `vmbr7` (Database Tier) | Automated Cold-Backup Sync Engine |
| **Internal Safe Proxy** | `10.10.10.10` | `internal.lab` | `vmbr1` (Safe Internal) | Nginx Safe Proxy (`nginx-safe`) |
| **Gitea Source Control** | `10.10.10.15` | `gitea.lab` | `vmbr1` (Safe Internal) | Self-Hosted Git Repository Server |
| **n8n Automation** | `10.10.10.25` | `n8n.lab` | `vmbr1` (Safe Internal) | Event & Incident Automation Engine |
| **Mosquitto MQTT** | `10.30.30.2` | `mqtt.lab` | `vmbr3` (IoT Zone) | Local IoT Sensor Telemetry Broker |
| **Home Assistant** | `10.30.30.5` | `ha.lab` | `vmbr3` (IoT Zone) | Central Home Automation Hub |
| **Short Link Manager** | `10.10.10.35` | `short.internal.lab` | `vmbr1` (Safe Internal) | Private 2-Page Shortener Web UI (:8080) |

---

## 🖧 Hardware MAC Addresses & WOL Reference

> **Note:** Exact hardware MAC addresses are maintained in the local gitignored `.env` file (see `.env.example`).

| Device / Interface | Variable in `.env` | IP Mapping | Notes |
| :--- | :--- | :--- | :--- |
| **Proxmox Laptop (Built-in LAN `enp12s0`)** | `MAC_PROXMOX_BUILTIN` | `192.168.1.2` | Primary Wake-on-LAN target |
| **Proxmox Legacy Lease (`eno1`)** | `MAC_PROXMOX_LEGACY` | `192.168.1.2` | Former static lease in `/etc/config/dhcp` |
| **Proxmox USB Adapter (USB passthrough / `eth6`)** | `MAC_PROXMOX_USB` | Dynamic / WAN | Former USB-Ethernet swing WAN (hotplugged `eth6` / replaced by VLAN 100 trunk `eth4`) |
| **ThinkPad Wi-Fi (`wlp3s0`)** | `MAC_PROXMOX_WIFI` | `192.168.1.153` | Internal wireless card (standby) |
| **Main Workstation PC** | `MAC_MAIN_PC` | `192.168.1.197` | HP EliteDesk Mini PC (Allowlisted) |
| **User Mobile Phone (`realme-P1-5G`)** | `MAC_PHONE` | `192.168.1.185` | Primary mobile device (Allowlisted) |
| **Pi-hole Container (LXC 205 `eth0`)** | `MAC_PIHOLE_OOB` | `192.168.1.135` | Out-of-Band DNS Sinkhole (Allowlisted) |
| **OpenWrt VM (VM 100 `eth0`)** | `MAC_OPENWRT_VM` | `192.168.1.129` | Virtual Core Router LAN Interface (Allowlisted) |
| **WAN Controller (LXC 200 `eth0`)** | `MAC_LXC_WAN_CONTROLLER` | `192.168.1.130` | Fail-safe Out-of-Band Dashboard (Allowlisted) |
| **ESP32 Dev Board** | `MAC_ESP32` | `10.30.30.10` / Dynamic | IoT Sensor / ESPHome Node (VLAN 30) |
| **ESP8266 Dev Board** | `MAC_ESP8266` | `10.30.30.11` / Dynamic | IoT Sensor Node (VLAN 30) |

---

## 🚦 Active Deployment & Service State Matrix

> **Note for Any Agent / Auditor:** This matrix distinguishes what is **actively running right now** versus what is an **architectural target / planned phase**.

| Service / Node | Platform | Network Location | Status | Current Details / Source Files |
| :--- | :--- | :--- | :--- | :--- |
| **Physical Gateway** | TP-Link Archer C6 v3 | `192.168.1.1` (LAN) | 🟢 **Live** | Mode 1 PPPoE, `wan-mode` script, strictorder DNS upstream, fw4 MAC allowlist & anti-bypass DNAT |
| **Proxmox Hypervisor** | ThinkPad Laptop | `192.168.1.2` (`vmbr0`) | 🟢 **Live** | PVE 9.2.2, kernel 7.0, `power-manager.sh` (`projects/00-proxmox-host/scripts/power-manager.sh`), `wake-proxmox` (`projects/00-proxmox-host/scripts/wake-proxmox`), `wol.service` |
| **Virtual Router (VM 100)** | OpenWrt 25.12.6 VM | `192.168.1.129` (`vmbr0`) | 🟢 **Live** | Standby `wan_vlan` (VLAN 100), gateway for `safe_internal`, `public_ingress`, and `ha_iot` zones |
| **WAN Controller (LXC 200)**| Debian 12 LXC | `192.168.1.130` (`vmbr0`) | 🟢 **Live** | Nginx + Python API (`projects/01-dual-openwrt-routing/wan-controller/app.py`), Web dashboard on port 80 |
| **Pi-hole DNS Sinkhole (LXC 205)**| Debian 12 LXC | `192.168.1.135` (`vmbr0`) | 🟢 **Live** | Pi-hole v6.5, StevenBlack adult & ad blocklists (148k domains), strict fallback upstream (`projects/07-pihole-dns-sinkhole`) |
| **Local Mini PC Services** | Docker on HP EliteDesk | `192.168.1.197` (LAN) | 🟢 **Live** | SearXNG, Ollama LLM, n8n (Local Docker Vaultwarden stopped; migrated to Proxmox) |
| **IoT Wi-Fi (VLAN 30)** | Archer C6 `radio0` | `10.30.30.0/24` (`vmbr3`) | 🟡 **Ready** | Specification complete (`EXP-003`). Ready to deploy upon entering hardware MACs. |
| **Public Reverse Proxy (`nginx-public` LXC 202)**| Debian 13 LXC | `10.20.20.10` (`vmbr2`) | 🟢 **Live** | Nginx reverse proxy + `cloudflared` tunnel daemon servicing `vault.snowfox.live` (`projects/02-per-zone-nginx-proxies`) |
| **Vaultwarden Production Service (LXC 220)** | Debian 13 LXC (Docker) | `10.20.20.11` (`vmbr2`) | 🟢 **Live** | Production Vaultwarden (`:8443` HTTPS via Homelab CA), signups active (`SIGNUPS_ALLOWED=true`), storage quotas enforced (10MB/100MB/50MB), 135 organized ciphers with native SSH Keys, backed by central PostgreSQL (`projects/03-vaultwarden-service`) |
| **Central Database Service (LXC 210)** | Debian 13 LXC | `10.70.70.10` (`vmbr7`) | 🟢 **Live** | Multi-tenant PostgreSQL 17.11 (`scram-sha-256`, SSL enforced) + Redis 7 (`projects/12-central-database-service`) |
| **Safe Internal Reverse Proxy (LXC 201)**| Proxmox LXC | `10.10.10.10` (`vmbr1`) | ⚪ **Planned** | Internal proxy for Gitea, Immich, n8n (`projects/02-per-zone-nginx-proxies`) |
| **Gitea Git Server (LXC 260)** | Proxmox LXC | `10.10.10.15` (`vmbr1`) | ⚪ **Planned** | Self-hosted Git server backed by central PostgreSQL (`db-central`) |
| **n8n Automation Engine (LXC 240)** | Proxmox LXC | `10.10.10.25` (`vmbr1`) | ⚪ **Planned** | Workflow & security incident automation hub (`projects/08-n8n-workflow-automation`) |
| **DBBackup Sync Container** | Proxmox LXC | `10.70.70.11` (`vmbr7`) | ⚪ **Planned** | Outbound cold-backup sync for Supabase & Neon, plus automated local pg_dumps |
| **Home Assistant Core** | Proxmox VM / LXC | `10.30.30.5` (`vmbr3`) | ⚪ **Planned** | Planned smart home hub with native Tailscale |
| **Mosquitto MQTT Broker** | Proxmox LXC | `10.30.30.2` (`vmbr3`) | ⚪ **Planned** | Planned broker for ESP32/ESP8266 telemetry (`EXP-003`) |
| **Suricata / Snort L7 DPI** | Proxmox LXC / VM | `10.50.50.10` (`vmbr5`) | ⚪ **Planned** | L7 deep packet inspection, TLS SNI filtering, and automated threat mitigation (`knowledge/security-anti-bypass-vpn-dns-defense`) |
| **Management Bots (LXC)** | Proxmox LXC | `10.60.60.10` (`vmbr6`) | ⚪ **Planned** | Planned isolated bot container with forced-command SSH wrapper |
| **Personal URL Shortener (`short.snowfox.live`)** | Cloudflare Edge Worker + LXC | Cloudflare Edge / `10.10.10.35` (`vmbr1`) | ⚪ **Planned** | Branded short-links (`short.snowfox.live`, BD Geo-fenced), private 2-page admin UI in `vmbr1`, 24/7 edge redirection (`projects/13-personal-url-shortener`) |

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
    HostName 192.168.1.185
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

### Canonical Host, Bridge & Guest Interface Map

| Proxmox Guest vNIC | Physical Port / Host Parent | Proxmox Bridge | OpenWrt Guest Device | Gateway / Subnet | Architectural Role | Current Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `net0` (`virtio`) | `enp12s0` (Built-in GbE) | `vmbr0` | `eth0` (`homelan`) | `192.168.1.129/24` | Management LAN & Mode 1 Gateway Link | 🟢 Live |
| `net1` (`virtio`) | *None (Host virtual)* | `vmbr1` | `eth1` (`safe_internal`)| `10.10.10.1/24` | Safe Internal Zone (Gitea, Immich, n8n) | 🟢 Live |
| `net2` (`virtio`) | *None (Host virtual)* | `vmbr2` | `eth2` (`public_ingress`)| `10.20.20.1/24`| Public Ingress (Nginx, Cloudflare, Vaultwarden) | 🟢 Live |
| `net3` (`virtio`) | `enp12s0.30` (VLAN 30) | `vmbr3` | `eth3` (`ha_iot`) | `10.30.30.1/24` | Isolated IoT & Home Assistant VLAN | 🟢 Live |
| `net4` (`virtio`) | `enp12s0.100` (VLAN 100)| `vmbr100`| `eth4` (`wan_vlan`) | Dynamic PPPoE | Trunked Direct ISP PPPoE Dialer (Mode 2/3) | 🟢 Live (Metric 10) |
| `net5` (`virtio`) | *None (Host virtual)* | `vmbr7` | `eth5` (`database`) | `10.70.70.1/24` | Dedicated Isolated Database Tier (`db-central`)| 🟢 Live |
| `usb0` (CDC Ether) | USB 2.0 Bus Passthrough | *Direct Guest USB* | `eth6` (`wan_fiber`) | Dynamic PPPoE | Direct Fiber Dongle (Emergency Backup WAN) | ⚪ Standby |
| *Pending* | *None (Host virtual)* | `vmbr4` | *Pending* | `10.40.40.1/24` | Unsafe Online Zone (*Arr, Torrent) | ⚪ Bridge Ready |
| *Pending* | *None (Host virtual)* | `vmbr5` | *Pending* | `10.50.50.1/24` | Direct Protocol DMZ (Asterisk, Mail) | ⚪ Bridge Ready |
| *Pending* | *None (Host virtual)* | `vmbr6` | *Pending* | `10.60.60.1/24` | Management Bots Zone (Telegram Bot) | ⚪ Bridge Ready |
