# 🧪 Homelab Engineering Lab Notebook

Welcome to the lab repository. This vault tracks all architecture experiments, failure logs, knowledge base articles, and operational runbooks across our homelab infrastructure.

---

## 🧭 Navigation & Core Indexes

- 🧰 **Hardware & Assets Inventory:** [inventory](inventory.md) (Physical nodes, microcontrollers, cloud accounts, domain, and running services)
- 📊 **Resource Planning & Hypervisor Constraints:** [resource-planning-and-limits](knowledge/resource-planning-and-limits.md) (RAM budgeting, LXC vs VM overhead, KSM deduplication, Debian 13 host parity)
- 💡 **Future Roadmap & Tech Backlog:** [future-roadmap](knowledge/future-roadmap.md) (Gitea, Headscale, NAS, Immich, Pi-hole, IPv6/DDNS, Arr stack, Kiwix, Home Assistant, Asterisk/VoIP)
- 📐 **Architecture Decisions (ADR):** [architecture-decisions](knowledge/architecture-decisions.md) (Permanent logs of network topologies, bridge designs, and security models)
- ⚠️ **Common Troubles & Quirks:** [common-troubles](knowledge/common-troubles.md) (Hardware crash recovery, driver workarounds)
- 🧠 **Mistakes to Avoid (Lessons Learned):** [mistakes-to-avoid](knowledge/mistakes-to-avoid.md)
- 🔧 **Troubleshooting Playbook:** [troubleshooting-playbook](knowledge/troubleshooting-playbook.md)
- 🤖 **Infrastructure-as-Code (IaC) Framework:** [iac-framework](iac/README.md) (Agentless pyinfra & POSIX playbooks for Proxmox hardening, WAN controller, OpenWrt, and Pi-hole)
- 📝 **New Experiment Template:** [experiment-template](templates/experiment-template.md)

> [!IMPORTANT]
> **Universal Service Granularity Standard:**  
> Every individual service, engine, or subsystem—regardless of scale or complexity (e.g. `00-proxmox-host`, `01-dual-openwrt-routing`, `03-vaultwarden-service`, `07-pihole-dns-sinkhole`, and future services like Gitea, n8n, Home Assistant, Immich, etc.)—**MUST maintain its own dedicated project directory** under `projects/XX-<service-name>/`.
> - Each project folder contains its own self-contained `README.md` (architecture, specs, dependencies), operational `runbook.md`, configuration templates, and experiment logs.
> - Inter-service relationships, hypervisor hosting (`00-proxmox-host`), and router firewall rules (`01-dual-openwrt-routing`) maintain explicit cross-links to the component's dedicated project directory.

---

## 🗺️ Master Network & Service Architecture

```mermaid
flowchart TD
    %% ==================================================
    %% 1. Physical Network, Gateway & WAN
    %% ==================================================
    subgraph PhysicalWAN["1. Physical Network & Hardware Layer"]
        ISP["ISP Fiber"] --> ONU["Fiber ONU"]
        ONU --> Router{"Physical Gateway<br/>TP-Link Archer C6 v3 (OpenWrt)<br/>192.168.1.1<br/>Mode 1 / Mode 2 / Mode 3 WAN"}

        Router -->|Parental Controls & Strict-Order DNS| Repeater["Wi-Fi Repeater"]
        Repeater --> Dad["Dad Phone (Restricted)"]
        Repeater --> Mom["Mom Phone (Restricted)"]

        Router -->|Allowlisted / Unrestricted LAN| PC["HP EliteDesk PC (192.168.1.197)"]
        Router -->|Allowlisted / Unrestricted Wi-Fi| MyPhone["My Phone (192.168.1.185)"]

        Router -->|Isolated 2.4GHz SSID: snowfox-iot| IoT_WiFi["Isolated IoT Wi-Fi<br/>snowfox-iot (VLAN 30)"]
        IoT_WiFi --> ESP32["ESP32 Dev Board"]
        IoT_WiFi --> ESP8266["ESP8266 Dev Board"]
    end

    %% ==================================================
    %% 2. Cloudflare 24/7 Edge & Remote Access Mesh
    %% ==================================================
    subgraph CloudEdge["2. Cloudflare 24/7 Edge & Remote Tailscale Mesh"]
        direction TB

        subgraph CloudflareEdge["Cloudflare 24/7 Global Edge"]
            direction TB
            CF_Worker["short.snowfox.live<br/>Cloudflare Worker + KV Edge<br/>(24/7 Bangladesh Geo-Fence)"]
            CF_Pages["simplearch.snowfox.live<br/>Cloudflare Pages"]
            CF_Tunnel["vault.snowfox.live<br/>Cloudflare Argo Tunnel (Encrypted)"]
            CF_DNS["Public Cloudflare DNS<br/>*.snowfox.live -> NXDOMAIN<br/>(Zero OSINT / Topology Leak)"]
        end

        subgraph RemoteMesh["Remote Clients Tier"]
            direction TB
            RemoteTailscale["Owner Remote Client<br/>(Phone / Laptop on Tailscale)"]
        end
    end

    %% ==================================================
    %% 3. Proxmox VE Hypervisor Host
    %% ==================================================
    subgraph ProxmoxHost["3. Proxmox VE Hypervisor - ThinkPad Host (192.168.1.2)"]
        direction TB

        PVE["Proxmox VE 9.2.2 Host<br/>Tailscale Subnet Router (100.127.129.106)<br/>Auto Power-Manager (12 AM Off / 7 AM RTC Wake)<br/>WoL Enabled (enp12s0)"]

        PhysicalNIC["Physical GbE NIC: enp12s0"]
        VMbr0["vmbr0 - Physical LAN / OOB Management<br/>192.168.1.0/24"]
        VMbr100["vmbr100 - Trunked WAN VLAN Bridge<br/>enp12s0.100 (Trunked to Router)"]

        PhysicalNIC --- VMbr0
        PhysicalNIC --- VMbr100
        VMbr0 --- PVE

        %% Out-of-band management services on vmbr0
        subgraph OOB["Out-of-Band Management Services (vmbr0)"]
            direction TB
            LXC200["🟢 LXC 200: wan-controller<br/>192.168.1.130:80<br/>WAN Mode Switcher & REST API<br/>wan.snowfox.live / wan.lab"]
            PiHoleOOB["🟢 LXC 205: pihole-oob<br/>192.168.1.135:80/53<br/>Pi-hole v6 Ad/Adult DNS Sinkhole<br/>Split-Horizon DNS (*.snowfox.live -> 10.10.10.10)"]
        end

        VMbr0 --- LXC200
        VMbr0 --- PiHoleOOB

        %% OpenWrt Core Router VM
        subgraph RouterVM["Virtual Core Router (VM 100)"]
            direction TB
            OpenWrt["🟢 OpenWrt 25.12.6 VM 100<br/>Core Firewall & Multi-Zone Router (192.168.1.129)<br/>VLAN 100 PPPoE Dialer (eth4 / Mode 2 & 3)<br/>Audited Cross-Zone Pinholes"]
        end

        VMbr0 ---|eth0: LAN Management| OpenWrt
        VMbr100 ---|eth4: Trunked PPPoE WAN| OpenWrt

        %% Alternate USB WAN
        USBNIC["USB-to-Ethernet Adapter (35b5:3500)<br/>CDC Ether (eth6 / Swing WAN)"]
        USBNIC -.->|Direct Passthrough| OpenWrt

        %% ==================================================
        %% 4. Proxmox Internal Bridges and Service Zones
        %% ==================================================
        subgraph Bridges["Proxmox Internal Isolated Bridges"]
            direction TB

            %% Safe internal zone (Applications Tier)
            subgraph ZoneSafe["Safe Internal Zone - vmbr1 (10.10.10.0/24)"]
                direction TB

                NginxSafe["🟢 LXC 201: nginx-safe (10.10.10.10)<br/>Split-Horizon Reverse Proxy (:443)<br/>Wildcard TLS: *.snowfox.live (Let's Encrypt)<br/>(Terraform Managed)"]

                N8N["🟢 LXC 240: n8n Automation Engine<br/>10.10.10.25:5678 (Native Node.js 22 LTS)<br/>https://n8n.snowfox.live<br/>(Terraform Managed)"]
                Mermaid["🟢 LXC 245: Mermaid Diagram Server<br/>10.10.10.26:80 (Native Nginx SPA)<br/>https://mermaid.snowfox.live<br/>(Terraform Managed)"]
                ShortManager["🟢 LXC 225: short-manager<br/>10.10.10.35:8080 (Python/Flask Web UI)<br/>https://short-admin.snowfox.live<br/>(Terraform Managed)"]
                Gitea["⚪ LXC 260: Gitea Git Server<br/>10.10.10.15:3000 (Planned)"]
                Immich["⚪ Immich (Planned)"]
                NAS["⚪ HDD NAS / FileBrowser (Planned)"]
                Bookstack["⚪ BookStack & Kiwix (Planned)"]
                Jellyfin["⚪ Jellyfin / Plex (Planned)"]

                NginxSafe --> N8N
                NginxSafe --> Mermaid
                NginxSafe --> ShortManager
                NginxSafe --> Gitea
                NginxSafe --> Immich
                NginxSafe --> NAS
                NginxSafe --> Bookstack
                NginxSafe --> Jellyfin
            end

            %% Dedicated Database & Data Protection Tier
            subgraph ZoneDB["Dedicated Database Tier - vmbr7 (10.70.70.0/24)"]
                direction TB

                Database["🟢 LXC 210: db-central (10.70.70.10)<br/>Multi-Tenant PostgreSQL 17 + Redis 7<br/>Strict SCRAM-SHA-256 Authentication"]
                DBBackup["⚪ DBBackup Engine (10.70.70.11)<br/>Cold-Pull: Supabase & Neon<br/>Automated pg_dump to Storage (Planned)"]

                DBBackup -.->|Local Dump Socket| Database
            end

            %% Public Ingress & Hardened Tier
            subgraph ZonePublicSafe["Public Ingress & Hardened Tier - vmbr2 (10.20.20.0/24)"]
                direction TB

                NginxPublic["🟢 LXC 202: nginx-public (10.20.20.10)<br/>cloudflared Ingress Tunnel Daemon<br/>Real-IP (CF-Connecting-IP)<br/>Stealth 404 /admin Lockdown"]
                Vaultwarden["🟢 LXC 220: Vaultwarden Production<br/>10.20.20.11:8443 (Mutual Internal PKI TLS)<br/>https://vault.snowfox.live"]

                NginxPublic --> Vaultwarden
            end

            %% Home Assistant & IoT Zone
            subgraph ZoneHA["Home Assistant & IoT Zone - vmbr3 (10.30.30.0/24)"]
                direction TB
                HA["⚪ Home Assistant Core (10.30.30.5)<br/>Native Tailscale Integration (Planned)"]
                MQTT_Local["⚪ Mosquitto MQTT Broker (10.30.30.2)<br/>ESP32 / ESP8266 Telemetry (Planned)"]
                HA --- MQTT_Local
            end

            %% Unsafe services
            subgraph ZoneUnsafe["Unsafe Online Services - vmbr4 (10.40.40.0/24)"]
                direction TB
                ArrStack["⚪ *Arr Stack & qBittorrent<br/>Direct Host Storage Mount (Planned)"]
            end

            %% VoIP / Direct Ingress DMZ
            subgraph ZoneDMZ["VoIP & Direct Ingress DMZ - vmbr5 (10.50.50.0/24)"]
                direction TB
                Asterisk["⚪ Asterisk / FreePBX VoIP (Planned)"]
                Mail["⚪ Self-Hosted Mail Server (Planned)"]
            end

            %% Dedicated Management Bots Zone
            subgraph ZoneBots["Management Bots Zone - vmbr6 (10.60.60.0/24)"]
                direction TB
                Telegram["⚪ Telegram Bots Hub<br/>Router Admin & Vaultwarden Bot (Planned)"]
            end
        end

        %% OpenWrt interfaces to isolated service bridges
        OpenWrt <-->|eth1: vmbr1| ZoneSafe
        OpenWrt <-->|eth2: vmbr2| ZonePublicSafe
        OpenWrt <-->|eth3: vmbr3| ZoneHA
        OpenWrt <-->|Pending: vmbr4| ZoneUnsafe
        OpenWrt <-->|Pending: vmbr5| ZoneDMZ
        OpenWrt <-->|Pending: vmbr6| ZoneBots
        OpenWrt <-->|eth5: vmbr7| ZoneDB

        %% Inter-bridge Database Pinholes
        N8N -.->|TCP:5432 Pinhole (n8n_db)| Database
        Vaultwarden -.->|TCP:5432 Pinhole (vaultwarden_db)| Database
        Gitea -.->|TCP:5432 Pinhole (gitea_db)| Database
        ShortManager -.->|Outbound HTTPS Link Sync| CF_Worker
        DBBackup -.->|Outbound WAN Sync| OpenWrt
    end

    %% External Cross-Connections
    Router -->|Single Trunk Cable: Untagged LAN + VLAN 100 WAN + VLAN 30 IoT| PhysicalNIC
    Router -.->|DNS Redirect / Intercept :53| PiHoleOOB
    Router -.->|7:00 AM Cron WoL Magic Packet| PhysicalNIC
    IoT_WiFi -.->|802.1Q VLAN 30 Trunk / MQTT:1883 Telemetry| ZoneHA

    RemoteTailscale ==>|Encrypted WireGuard Mesh (100.64.0.0/10)| PVE
    PVE -.->|DNAT :80,:443 to 10.10.10.10| NginxSafe
    PVE -.->|DNAT :53 to 192.168.1.135| PiHoleOOB

    CF_Tunnel ==>|Encrypted Tunnel: snowfox-tunnel| NginxPublic
    NginxSafe -.->|OOB Proxy: https://pve.snowfox.live -> :8006| PVE
    NginxSafe -.->|OOB Proxy: https://router.snowfox.live -> :443| Router
    NginxSafe -.->|OOB Proxy: https://pihole.snowfox.live -> :80| PiHoleOOB
    NginxSafe -.->|OOB Proxy: https://wan.snowfox.live -> :80| LXC200
```

---

## 📂 Active Projects & Experiments

### 0. Proxmox Hypervisor Host Operations
- **Directory:** `projects/00-proxmox-host/`
- **Documentation:** [Proxmox Host Operations Runbook](projects/00-proxmox-host/runbook.md)
- **Covers:** Lid-close sleep masking, power schedule (12:00 AM shut down / 7:00 AM wake via RTC), low-battery protection (<40%), terminal broadcast warnings, and bridge network layouts.

### 1. Dual OpenWrt Routing & Dynamic Failover
- **Directory:** `projects/01-dual-openwrt-routing/`
- **Current Live Status:** Succeeded & Verified
- **Experiments:**
  - [EXP-001: Dual OpenWrt WAN Failover with Metric Switching](projects/01-dual-openwrt-routing/experiments/001-failover-wan.md) *(SUCCEEDED)*
  - [EXP-002: Single-Cable VLAN Trunking & Multi-Mode Dual PPPoE](projects/01-dual-openwrt-routing/experiments/002-vlan-trunking.md) *(SUCCEEDED)*
- **Runbook:** [Routing Operations & wan-mode Runbook](projects/01-dual-openwrt-routing/runbook.md)

### 2. Per-Zone Nginx Reverse Proxies & WAN Dashboard
- **Directory:** `projects/02-per-zone-nginx-proxies/`
- **Documentation:** [Per-Zone Nginx Reverse Proxy Architecture](projects/02-per-zone-nginx-proxies/README.md)
- **Engineering Guide:** [Split-Horizon DNS & Wildcard HTTPS Engineering Guide](projects/02-per-zone-nginx-proxies/split-horizon-dns-guide.md)
- **Covers:** Out-of-band WAN Controller (`192.168.1.130`), Public Ingress Proxy (`10.20.20.10`), Safe Internal Proxy (`nginx-safe` on `10.10.10.10`), and Split-Horizon DNS (`*.snowfox.live`) with automated Let's Encrypt wildcard certificates via Cloudflare DNS-01.

### 3. Vaultwarden Production Service & Monetization
- **Directory:** `projects/03-vaultwarden-service/`
- **Documentation:** [Vaultwarden Production Architecture & Monetization Blueprint](projects/03-vaultwarden-service/README.md)
- **Covers:** Ingress topology, Bangladesh-only GeoIP fencing, `/admin` lockdown to 404, HTTP security headers, and the bKash/Nagad pay-to-invite onboarding workflow.

### 4. Monetized OpenWrt Captive Portal & Wi-Fi Billing
- **Directory:** `projects/04-monetized-captive-portal/`
- **Documentation:** [Monetized OpenWrt Captive Portal & Wi-Fi Billing Architecture](projects/04-monetized-captive-portal/README.md)
- **Covers:** Automated Wi-Fi monetization, openNDS/CoovaChilli engines, voucher billing, bKash/Nagad integration, and session quotas.

### 5. OpenWrt Simple Local Web UI
- **Directory:** `projects/05-openwrt-simple-webui/`
- **Documentation:** [OpenWrt Simple Web UI Architecture & Spec](projects/05-openwrt-simple-webui/README.md)
- **Covers:** Offline-first SPA under 200KB, ubus/JSON-RPC, wizard setup, device access lists, parental control, and 60-second safety auto-rollback engine.

### 6. OpenWrt Telegram Remote Control Bot
- **Directory:** `projects/06-openwrt-telegram-bot/`
- **Documentation:** [OpenWrt Telegram Remote Control Bot Architecture & Spec](projects/06-openwrt-telegram-bot/README.md)
- **Covers:** Safe remote commands, PPPoE/reset protection boundary, unknown station join alerts with [Allow] button, numeric ID allowlist, and off-router prototype vs on-router deployment.

### 7. Pi-hole Out-of-Band DNS Sinkhole & Parental Controls
- **Directory:** `projects/07-pihole-dns-sinkhole/`
- **Documentation:** [Pi-hole Out-of-Band DNS Sinkhole & Parental Controls Architecture](projects/07-pihole-dns-sinkhole/README.md)
- **Runbook:** [Pi-hole Operations & Maintenance Runbook](projects/07-pihole-dns-sinkhole/runbook.md)
- **Current Live Status:** Live & Verified (Proxmox LXC 205 at `192.168.1.135` on `vmbr0`)
- **Covers:** Hardware offload from Archer C6, StevenBlack unified adult & ad blocklists (148k domains), universal network-wide baseline, strict sequential upstream failover (`1.1.1.3` Cloudflare for Families during Proxmox midnight-7 AM sleep), and anti-bypass firewall DNAT/port 853 drops.

### 8. n8n Low-Code Workflow Automation Engine
- **Directory:** `projects/08-n8n-workflow-automation/`
- **Documentation:** [n8n Workflow Automation Hub Architecture](projects/08-n8n-workflow-automation/README.md)
- **Status:** Planned / Architecture & Security Blueprint
- **Covers:** Low-code event pipeline engine, 10-minute Have I Been Pwned (HIBP) vault credential breach detection watchdog, automated high-entropy password regeneration with historical retention, and cross-service webhook orchestration.

### 9. Centralized Telegram Bot & Alerting Hub
- **Directory:** `projects/09-telegram-bot-hub/`
- **Documentation:** [Centralized Telegram Bot & Alerting Hub](projects/09-telegram-bot-hub/README.md)
- **Status:** Planned / Architecture & Security Blueprint
- **Covers:** Central incident dispatching layer, interactive inline remediation buttons, direct password reset URL resolution (`/.well-known/change-password`), Proxmox SMART/backup alerts, and multi-service incident escalation.

### 10. Workstation Antivirus / EDR Stack & Incident Auto-Response
- **Directory:** `projects/10-workstation-av-edr-stack/`
- **Documentation:** [Workstation Antivirus / EDR Stack & Incident Auto-Response Architecture](projects/10-workstation-av-edr-stack/README.md)
- **Status:** Planned / Architecture & Integration Blueprint
- **Covers:** Host-level endpoint defense on Main PC (`rubait`), ClamAV signatures, YARA rules, osquery, eBPF telemetry, local Ollama AI alert triage, and automated info-stealer scans cascading from Vaultwarden breach reports.

### 11. Multi-WAN Load Balancing (`mwan3`)
- **Directory:** `projects/11-multiwan-load-balancing/`
- **Documentation:** [Multi-WAN Load Balancing Architecture](projects/11-multiwan-load-balancing/README.md)
- **Runbook:** [Multi-WAN Load Balancing Operations & Verification Runbook](projects/11-multiwan-load-balancing/runbook.md)
- **Status:** Staged & Documented (Awaiting Off-Peak Testing Window)
- **Covers:** Simultaneous dual-PPPoE traffic splitting (Mode 3), sticky HTTPS persistence (port 443), P2P/torrent VM offload, sub-5-second ICMP health tracking, and zero-downtime safety rollback.

### 12. Centralized Multi-Tenant Database Service (`db-central`)
- **Directory:** `projects/12-central-database-service/`
- **Documentation:** [Central Database Service Architecture](projects/12-central-database-service/README.md)
- **Current Live Status:** Provisioned on Proxmox (LXC 210 on `vmbr7` at `10.70.70.10`)
- **Covers:** Debian 13 host parity, dedicated database tier (`vmbr7`), role-and-database level multi-tenancy, Vaultwarden/Gitea/n8n pinhole routing, zero-WAN-egress isolation, and companion cloud backup landing zone for Neon & Supabase.

### 13. Personal Branded URL Shortener (`short.snowfox.live`)
- **Directory:** `projects/13-personal-url-shortener/`
- **Documentation:** [Personal URL Shortener Architecture](projects/13-personal-url-shortener/README.md)
- **Status:** Planned / Architecture & Implementation Specification
- **Covers:** Cloudflare Worker + KV edge redirection (24/7 zero-downtime), strict Bangladesh-only geo-fence (`request.cf.country === 'BD'`), and private air-gapped 2-page admin UI in Safe Internal Zone (`vmbr1`, `10.10.10.35` / `short.internal.lab`) synchronizing with Cloudflare via outbound-only HTTPS.
