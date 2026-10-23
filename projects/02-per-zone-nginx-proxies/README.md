# 🛡️ Per-Zone Reverse Proxy & Out-of-Band Management Architecture

> **Project ID:** `02-per-zone-nginx-proxies`  
> **Status:** Phase 1 Completed (`wan-controller` on `vmbr0`)  
> **Architecture Principle:** Strict Network Segmentation via Isolated Reverse Proxies with Independent Out-of-Band Physical Management  
> **Authoritative ADR:** [[lab/knowledge/architecture-decisions#ADR-001 Master Topology Refinement and Ingress Egress Realignment|ADR-001 (Master Topology & Bridges)]]

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
Central DB, n8n,          Vaultwarden,              HA Core, Mosquitto    Tor obfs4, *Arr,      Asterisk FreePBX,     Router Controller,
Gitea, Immich, NAS,       Headscale Control         MQTT, ESP Sensors     qBittorrent (Shared   Self-Hosted Mail      Vaultwarden Bot
BookStack, Kiwix          (Cloudflare Tunnel)       (Tailscale Native)    Host Storage Mount)   (Fail2ban)            (Audited Pinholes)
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
  - `Vaultwarden`: Password manager vault (locked down `/admin`, MFA required)
  - `Headscale`: Self-hosted Tailscale coordination server
- **Firewall Policy:** Traffic can only enter via Cloudflare Tunnel. Strictly isolated: cannot initiate connections into `vmbr1` (Safe Internal) or `vmbr0` (Home LAN).

### 3.3 Zone 3: Home Assistant & IoT (`vmbr3` - `10.30.30.0/24`)
- **Gateway:** `10.30.30.1` (OpenWrt `eth3`)
- **Reverse Proxy:** **None** (Home Assistant has native Tailscale integration).
- **Access Model:** Tailscale mesh for remote control + local IoT devices.
- **Hosted Services:**
  - `Home Assistant Core` and smart home integrations (Zigbee, Matter, ESPHome).
  - `Local MQTT Broker (Mosquitto)`: Dedicated message broker for local ESP32/ESP8266 telemetry.
- **Firewall Policy:** Isolated from internal data storage (`vmbr1`). Home Assistant can poll IoT endpoints, but IoT devices cannot reach any other zone.

### 3.4 Zone 4: Unsafe / Online Workloads (`vmbr4` - `10.40.40.0/24`)
- **Gateway:** `10.40.40.1` (OpenWrt `eth4`)
- **Reverse Proxy:** **None** (Outbound only).
- **Access Model:** Services in this zone initiate outbound connections to the internet or connect through external VPNs/proxies.
- **Hosted Services:**
  - `Tor Node`: Anti-censorship relay / bridge (`obfs4`)
  - `*Arr Stack & qBittorrent`: Media indexers and P2P downloaders (bound to VPN).
  - **Storage Architecture:** Media is written to host-level shared storage via Proxmox bind mounts (`/mnt/storage/media`), eliminating the need for network file-sharing pinholes into `vmbr1`.
- **Firewall Policy:** Drop all packets destined for `vmbr0`, `vmbr1`, `vmbr2`, `vmbr3`, `vmbr5`, or `vmbr6`. Completely quarantined.

### 3.5 Zone 5: Protocol Direct DMZ (`vmbr5` - `10.50.50.0/24`)
- **Gateway:** `10.50.50.1` (OpenWrt `eth5`)
- **Reverse Proxy:** **None** (Non-HTTP protocol services).
- **Access Model:** Direct port forwarding through OpenWrt firewall with strict Fail2ban / CrowdSec IP banning.
- **Hosted Services:**
  - `Asterisk / FreePBX`: VoIP & VoWiFi PBX (SIP UDP/TCP 5060, RTP UDP range)
  - `Self-Hosted Mail`: Mail transfer agent (SMTP 25/587/465, IMAP 993)
- **Firewall Policy:** Strict port forwarding pinholes; rate-limiting; hard isolation preventing access to `vmbr1` internal services.

### 3.6 Zone 6: Management & Telegram Bots (`vmbr6` - `10.60.60.0/24`)
- **Gateway:** `10.60.60.1` (OpenWrt `eth6`)
- **Reverse Proxy:** **None** (Outbound polling to `api.telegram.org`).
- **Access Model:** Dedicated bot runtime zone with audited firewall pinholes.
- **Hosted Services:**
  - `Router Controller Bot`: Telegram bot managing physical router and VM link states.
  - `Vaultwarden Onboarding Bot`: Bot automating pay-to-invite onboarding.
- **Firewall Policy:** Default drop toward all zones; explicit pinholes permitted only for:
  - Destination `192.168.1.1:22` (Router SSH execution)
  - Destination `10.20.20.11:8085` (Vaultwarden API)

---

## 🐛 4. Provisioning Notes & Fixes Implemented

1. **Proxmox LXC Systemd Nesting:** Configured `pct set 200 --features nesting=1` to allow systemd inside Debian 12 unprivileged containers.
2. **Daemon Deployment:** Python web service cleanly transferred and managed via `systemctl enable --now wan-webui.service`.
3. **SSH Host Key Pinning (StrictHostKeyChecking Hardened):**
   - Public key auth established between `root@wan-controller` and physical router (`192.168.1.1`).
   - Hardened `app.py`: Removed all insecure `-o StrictHostKeyChecking=no` flags.
   - Pinned physical router's host ed25519 key into `/root/.ssh/known_hosts` inside LXC 200 using `ssh-keyscan -H 192.168.1.1` to eliminate MITM attack vectors.

---

## 📋 5. Next Implementation Milestones

- [ ] **Configure Proxmox Bridges:** Define `vmbr1`, `vmbr2`, `vmbr3`, `vmbr4`, `vmbr5` in `/etc/network/interfaces` on Proxmox host.
- [ ] **OpenWrt VM Virtual NICs:** Attach virtual interfaces for each bridge (`eth1` through `eth5`) to VM 100.
- [ ] **Deploy `nginx-safe` (LXC 201):** Debian 12 on `vmbr1` (`10.10.10.10`) for Safe Internal services.
- [ ] **Deploy `nginx-public` (LXC 202):** Debian 12 on `vmbr2` (`10.20.20.10`) running `cloudflared` for Vaultwarden and Headscale.
- [ ] **Configure OpenWrt Firewall Zones:** Establish zone drop rules enforcing unidirectional egress and strict quarantine for `vmbr4` and `vmbr5`.
