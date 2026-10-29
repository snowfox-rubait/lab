# 🛡️ Per-Zone Reverse Proxy & Out-of-Band Management Architecture

> **Project ID:** `02-per-zone-nginx-proxies`  
> **Status:** Phase 2 Completed (`wan-controller` on `vmbr0`, `nginx-safe` live on `vmbr1`)  
> **Architecture Principle:** Strict Network Segmentation via Isolated Reverse Proxies with Independent Out-of-Band Physical Management  
> **Authoritative ADR:** [ADR-001 (Master Topology & Bridges)](../../knowledge/architecture-decisions.md#adr-001-master-topology-refinement-and-ingress-egress-realignment)

---

## 🎯 1. Network Topology & Proxy Boundaries

To maintain high availability and defense-in-depth, the network is partitioned into two distinct management realms:
1. **Out-of-Band Physical Management (`vmbr0` / Home LAN):** Sits directly on the physical router's LAN. It does **not** rely on the OpenWrt VM. If the OpenWrt VM crashes, hangs, or is powered down, this out-of-band management interface remains 100% operational.
2. **Per-Zone Virtual Security Segments (`vmbr1` through `vmbr5`):** Governed strictly by the OpenWrt VM (VM 100). Reverse proxies are only deployed in zones that genuinely require layer-7 HTTP/HTTPS ingress, preventing lateral movement across zones.

```
                              ┌─────────────────────────────────────────────────────────┐
                              │                 Physical Router (192.168.1.1)            │
                              └────────────────────────────┬────────────────────────────┘
                                                           │
                                             vmbr0 Physical LAN (192.168.1.0/24)
                                    ┌──────────────────────┴──────────────────────┐
                                    │                                             │
                           [ Out-of-Band Controller ]                    [ OpenWrt VM (VM 100) ]
                             LXC 200 (192.168.1.130)                     WAN: 192.168.1.129
                             (Independent Fail-safe)                               │
        ┌─────────────────────────┬─────────────────────────┬─────────────────────┬─────────────────────┬─────────────────────┐
        │ vmbr1 (Safe Internal)   │ vmbr2 (Public Ingress)  │ vmbr3 (IoT / HA)    │ vmbr4 (Unsafe Online)│ vmbr5 (Protocol DMZ)│ vmbr6 (Mgmt Bots)
        │ 10.10.10.0/24           │ 10.20.20.0/24           │ 10.30.30.0/24       │ 10.40.40.0/24       │ 10.50.50.0/24       │ 10.60.60.0/24
        ▼                         ▼                         ▼                     ▼                     ▼                     ▼
[ nginx-safe (LXC 201) ]   [ nginx-public (LXC 202) ]   [ Home Assistant ]   [ Direct Outbound NAT ] [ Direct Port DMZ ]   [ Telegram Bots ]
 10.10.10.10               10.20.20.10                   10.30.30.10          (No Ingress Proxy)     (No HTTP Proxy)       (Dedicated Egress)
        │                         │                         │                     │                     │                     │
┌───────┴────────┐       ┌────────┴────────┐       ┌────────┴────────┐   ┌────────┴────────┐   ┌────────┴────────┐   ┌────────┴────────┐
Central DB, n8n,          Vaultwarden Service       HA Core, Mosquitto    *Arr, qBittorrent,    Asterisk FreePBX,     Router Controller,
Gitea, Immich, NAS,       (Sole Public Service)     MQTT, ESP Sensors     Local Lab Pipelines   Self-Hosted Mail      Vaultwarden Bot
BookStack, Kiwix          (Cloudflare Tunnel)       (Tailscale Native)    Host Storage Mount    (Fail2ban)            (Audited Pinholes)
```

---

## 🖥️ 2. Out-of-Band Component: `wan-controller` (LXC 200 on `vmbr0`)

### 2.1 Why LXC 200 Lives on `vmbr0`
- **Fail-safe Survival:** Communicates directly with the physical router (`192.168.1.1`). If the OpenWrt VM is completely dead, broken, or misconfigured during testing, you can still open `http://192.168.1.130/` from any phone or PC on the home Wi-Fi and switch WAN modes or inspect physical link state.
- **Role:** Pure physical infrastructure management (WAN Mode 1/2/3 switching & physical telemetry), NOT an application proxy.

### 2.2 Container Specifications
- **Container ID:** `200`
- **Hostname:** `wan-controller` (formerly `nginx-home`)
- **OS Template:** Debian 12 (Bookworm) standard amd64
- **Assigned Resources:** 1 Core, 512 MB RAM, 512 MB Swap, 4 GB Disk
- **Network Interface:** `eth0` attached to `vmbr0` (Physical LAN Bridge)
- **Static IP:** `192.168.1.130/24` (Gateway: `192.168.1.1`)
- **Web Port:** `80` (HTTP)

### 2.3 Workflow
1. Client accesses `http://192.168.1.130/`.
2. Nginx serves the dashboard SPA and proxies `/api/*` to a local Python daemon on `127.0.0.1:8080`.
3. The daemon uses automated passwordless SSH key authentication (`/root/.ssh/id_ed25519`) to execute `/usr/bin/wan-mode` on the physical router (`192.168.1.1`).

---

## 🛡️ 3. Per-Zone Segments (Behind OpenWrt VM)

All homelab services live behind the OpenWrt VM, partitioned by protocol, access pattern, and threat profile:

### 3.1 Zone 1: Safe Internal (`vmbr1` - `10.10.10.0/24`)
- **Gateway:** `10.10.10.1` (OpenWrt `eth1`)
- **Reverse Proxy:** `nginx-safe` (LXC 201, `10.10.10.10`)
- **Access Model:** Internal-only. Tailscale mesh + Cloudflare gray DNS records (resolving to local/tailnet IPs). Zero public ingress.
- **Hosted Services:**
  - `Database`: Central PostgreSQL / Redis for local microservices
  - `DBBackup`: Outbound pull worker for Supabase & Neon cold backup dumps (direct outbound NAT route; **no Nginx virtual host**)
  - `n8n`: Private workflow automation engine
  - `Gitea`: Self-hosted code repository
  - `Immich`: Mobile photo backup & AI library
  - `NAS`: HDD file storage (FileBrowser / Samba / OMV)
  - `BookStack`: Private knowledge documentation
  - `Kiwix`: Offline compressed Wikipedia / ZIM archive
  - `Jellyfin`: Local media streaming
- **Firewall Policy:** Outbound internet access allowed via NAT; inbound internet access completely blocked.

### 3.2 Zone 2: Safe Public Ingress (`vmbr2` - `10.20.20.0/24`)
- **Gateway:** `10.20.20.1` (OpenWrt `eth2`)
- **Reverse Proxy:** `nginx-public` (LXC 202, `10.20.20.10`)
- **Access Model:** Inbound access via Cloudflare Tunnel (`cloudflared`) with Cloudflare Orange Proxy, GeoIP restrictions, and TLS termination.
- **Hosted Services:**
  - `Vaultwarden`: Password manager vault (locked down `/admin`, MFA required, HTTPS `:8443` via internal Homelab PKI)
  - *(Note: Headscale has been decoupled from `vmbr2` and deferred as undecided)*
- **Firewall Policy:** Traffic can only enter via Cloudflare Tunnel. Strictly isolated: cannot initiate connections into `vmbr1` (Safe Internal) or `vmbr0` (Home LAN).

### 3.3 Zone 3: Home Assistant & IoT (`vmbr3` - `10.30.30.0/24`)
- **Gateway:** `10.30.30.1` (OpenWrt `eth3`)
- **Reverse Proxy:** **None** (Home Assistant has native Tailscale integration).
- **Access Model:** Tailscale mesh for remote control + local IoT devices via dedicated 2.4GHz Wi-Fi (`snowfox-iot` via 802.1Q VLAN 30 trunk).
- **Hosted Services:**
  - `Home Assistant Core` and smart home integrations (Zigbee, Matter, ESPHome).
  - `Local MQTT Broker (Mosquitto)`: Dedicated message broker for local ESP32/ESP8266 telemetry.
- **Physical Ingress & Security Policy (ADR-003):**
  - Physical Archer C6 router broadcasts dedicated 2.4GHz SSID with reduced TX power (10 dBm) and client isolation (`isolate '1'`).
  - Strict Layer-2 802.11 MAC filtering allowlist exclusively for ESP32 and ESP8266 hardware MACs (tracked in `.env`).
  - Bridged into `vmbr3` via 802.1Q VLAN 30 over the existing inter-router trunk link.
  - Zero access to Home LAN (`vmbr0`), router admin (SSH/LuCI), internal storage (`vmbr1`), or external WAN (optional UDP 123 NTP). IoT microcontrollers can only publish/subscribe to Mosquitto (`10.30.30.2:1883`).

### 3.4 Zone 4: Unsafe / Online Workloads (`vmbr4` - `10.40.40.0/24`)
- **Gateway:** `10.40.40.1` (Target OpenWrt interface)
- **Reverse Proxy:** **None** (Outbound only).
- **Access Model:** Services in this zone initiate outbound connections to the internet or connect through external VPNs/proxies.
- **Hosted Services:**
  - `*Arr Stack & qBittorrent`: Media indexers and P2P downloaders (bound to VPN).
  - **Storage Architecture & Privilege Separation:**
    - Download cache: `/mnt/storage/downloads` $\rightarrow$ Mounted Read/Write into `qBittorrent` and `*Arr`.
    - Final Media Library: `/mnt/storage/media` $\rightarrow$ Mounted Read-Only (`ro=1`) into `Jellyfin` and general NAS shares.
    - Prevents any compromised downloader in `vmbr4` from tampering with or destroying the main media or photo library.
- **Firewall Policy:** Drop all packets destined for `vmbr0`, `vmbr1`, `vmbr2`, `vmbr3`, `vmbr5`, or `vmbr6`. Completely quarantined.

### 3.5 Zone 5: Protocol Direct DMZ (`vmbr5` - `10.50.50.0/24`)
- **Gateway:** `10.50.50.1` (Target OpenWrt interface)
- **Reverse Proxy:** **None** (Non-HTTP protocol services).
- **Access Model:** Direct port forwarding through OpenWrt firewall with strict Fail2ban / CrowdSec IP banning.
- **Hosted Services:**
  - `Asterisk / FreePBX`: VoIP & VoWiFi PBX (SIP UDP/TCP 5060, RTP UDP range)
  - `Self-Hosted Mail`: Mail transfer agent (SMTP 25/587/465, IMAP 993)
- **Firewall Policy:** Strict port forwarding pinholes; rate-limiting; hard isolation preventing access to `vmbr1` internal services.

### 3.6 Zone 6: Management & Telegram Bots (`vmbr6` - `10.60.60.0/24`)
- **Gateway:** `10.60.60.1` (Target OpenWrt interface)
- **Reverse Proxy:** **None** (Outbound polling to `api.telegram.org`).
- **Access Model:** Dedicated bot runtime zone with audited firewall pinholes.
- **Hosted Services:**
  - `Router Controller Bot`: Telegram bot managing physical router and VM link states.
  - `Vaultwarden Onboarding Bot`: Bot automating pay-to-invite onboarding.
- **Firewall Policy & Security Boundaries:**
  - Default drop toward all zones; explicit pinholes permitted only for:
    - Destination `192.168.1.1:22` (Router SSH restricted via forced-command script)
    - Destination `10.20.20.11:8443` (Vaultwarden API: `POST /admin/invite` with admin token via internal HTTPS)
  - **SSH Hard Boundary Enforcement:** Dropbear on the router enforces `command="/usr/bin/bot-command-wrapper",no-pty,restrict` on the bot's public key, preventing any interactive root shell, PPPoE password reads, or factory resets.

### 3.7 Zone 7: Dedicated Database Tier (`vmbr7` - `10.70.70.0/24`)
- **Gateway:** `10.70.70.1` (OpenWrt `eth5` / `net5`)
- **Reverse Proxy:** **None** (Offline compute tier, zero direct internet egress).
- **Access Model:** Internal database socket access strictly through audited firewall pinholes.
- **Hosted Services:**
  - `db-central` (LXC 210, `10.70.70.10`): Central PostgreSQL 17.11 & Redis 7 cluster.
  - `DBBackup` (LXC, `10.70.70.11`): Automated local database dumps & cloud sync (Supabase/Neon).
- **Firewall Policy & Security Boundaries:**
  - Default drop on all cross-zone traffic; pinholes permitted only for:
    - Vaultwarden (`10.20.20.11`) $\rightarrow$ PostgreSQL (`10.70.70.10:5432` with SCRAM-SHA-256 and SSL enforced).
    - Safe Internal (`10.10.10.0/24` - Gitea, Immich, n8n) $\rightarrow$ PostgreSQL (`:5432`) & Redis (`:6379`).
  - Outbound internet access completely blocked for `db-central`.

---

## 🛠️ 4. Reverse Proxy Implementation Artifacts

### 4.1 Safe Internal Proxy (`nginx-safe` on LXC 201 `10.10.10.10` / `vmbr1`)
- **Virtual Host Configuration:** [`nginx-safe.conf`](nginx-safe.conf)
  - Terminates `*.snowfox.live` with valid Let's Encrypt wildcard certificate via standard port 443.
  - Proxies:
    - `pve.snowfox.live` $\rightarrow$ `192.168.1.2:8006` (Proxmox VE Web UI + WebSocket NoVNC)
    - `router.snowfox.live` $\rightarrow$ `192.168.1.1:80` (Physical Archer C6 LuCI)
    - `wan.snowfox.live` $\rightarrow$ `192.168.1.130:80` (WAN Controller LXC 200)
    - `pihole.snowfox.live` $\rightarrow$ `192.168.1.135:80` (Pi-hole OOB Console)
    - `gitea.snowfox.live` $\rightarrow$ `10.10.10.15:3000` (Gitea Git Server)
    - `n8n.snowfox.live` $\rightarrow$ `10.10.10.25:5678` (n8n Workflow Engine)
    - `short-admin.snowfox.live` $\rightarrow$ `10.10.10.35:8080` (Project 13 Short Link Manager)
    - `ha.snowfox.live` $\rightarrow$ `10.30.30.5:8123` (Home Assistant Core)
- **Wildcard Certificate Provisioner (DNS-01):** [`scripts/issue-wildcard-cert.sh`](scripts/issue-wildcard-cert.sh)
- **OpenWrt Split-Horizon DNS Configurator:** [`scripts/setup-split-dns-openwrt.sh`](scripts/setup-split-dns-openwrt.sh)
- **Complete Runbook:** [Split-Horizon DNS & Wildcard HTTPS Engineering Guide](split-horizon-dns-guide.md)

### 4.2 Public Ingress Proxy (`nginx-public` on LXC 202 `10.20.20.10` / `vmbr2`)
- **Virtual Host Configuration:** [`nginx-public.conf`](nginx-public.conf)
  - Services `vault.snowfox.live` via Cloudflare Tunnel daemon (`cloudflared`).

---

## 📋 5. Implementation Milestones

- [x] **Configure Proxmox Bridges:** Defined `vmbr0`–`vmbr7`, `vmbr100` in `/etc/network/interfaces` on Proxmox host.
- [x] **OpenWrt VM Virtual NICs:** Attached virtual interfaces for bridges to VM 100.
- [x] **Deploy `nginx-public` (LXC 202):** Debian 13 on `vmbr2` (`10.20.20.10`) running `cloudflared` tunnel for Vaultwarden with Bangladesh Geo-Fence.
- [x] **Design & Blueprint `nginx-safe` (LXC 201):** Configured [`nginx-safe.conf`](nginx-safe.conf), wildcard cert generator, and OpenWrt Split-Horizon DNS automation ([ADR-008](../../knowledge/architecture-decisions.md#adr-008-split-horizon-dns-with-wildcard-lets-encrypt-via-dns-01-for-zero-leak-internal-https)).
- [x] **Deploy `nginx-safe` Container:** Launched Debian 13 LXC 201 on `vmbr1` (`10.10.10.10`), deployed [`nginx-safe.conf`](nginx-safe.conf), and enabled Split-Horizon DNS resolution for `*.snowfox.live` across physical router and Pi-hole.
- [ ] **Configure OpenWrt Firewall Zones:** Establish zone drop rules enforcing unidirectional egress and strict quarantine for `vmbr4` and `vmbr5`.
