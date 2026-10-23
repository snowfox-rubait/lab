# 🧪 Homelab Engineering Lab Notebook

Welcome to the lab repository. This vault tracks all architecture experiments, failure logs, knowledge base articles, and operational runbooks across our homelab infrastructure.

---

## 🧭 Navigation & Core Indexes

- 🧰 **Hardware & Assets Inventory:** [[inventory]] (Physical nodes, microcontrollers, cloud accounts, domain, and running services)
- 💡 **Future Roadmap & Tech Backlog:** [[lab/knowledge/future-roadmap|future-roadmap]] (Gitea, Headscale, NAS, Immich, Pi-hole, IPv6/DDNS, Arr stack, Kiwix, Home Assistant, Tor, Asterisk/VoIP)
- 🧠 **Mistakes to Avoid (Lessons Learned):** [[lab/knowledge/mistakes-to-avoid|mistakes-to-avoid]]
- 🔧 **Troubleshooting Playbook:** [[lab/knowledge/troubleshooting-playbook|troubleshooting-playbook]]
- 📝 **New Experiment Template:** [[lab/templates/experiment-template|experiment-template]]

---

## 🗺️ Master Network & Service Architecture

```mermaid
flowchart TD
    %% ==================================================
    %% Physical Layer & WAN
    %% ==================================================
    subgraph PhysicalWAN ["Physical & Ingress Network"]
        ISP["ISP"] --> ONU["ONU"]
        ONU --> C{"Physical Router (OpenWrt Archer C6)"}
        
        C -->|Parental Control / Isolated| Repeater["Wi-Fi Repeater"]
        Repeater --> Dad["Dad's Phone"]
        Repeater --> Mom["Mom's Phone"]
        
        C --> MyPhone["My Phone"]
        C --> PC["HP EliteDesk PC"]
    end

    %% ==================================================
    %% Proxmox Host (ThinkPad)
    %% ==================================================
    subgraph ProxmoxHost ["Proxmox VE Hypervisor (ThinkPad Laptop)"]
        direction TB
        PVE["Proxmox Host (PVE OS)<br/>Tailscale | CrowdSec / Fail2ban"]
        C ---|Physical NIC vmbr0| PVE

        subgraph OutOfBand ["Out-of-Band Management (vmbr0 - 192.168.1.0/24)"]
            LXC200["LXC 200: WAN Controller Web UI"]
            PiHoleOOB["LXC: Pi-hole DNS Sinkhole"]
        end
        PVE --- OutOfBand

        N{"OpenWrt VM (Core Router)"}
        PVE --- N
        
        USB_NIC["USB-to-Ethernet Adapter"] -.->|Passthrough when needed| N
        USB_NIC -.->|Manual Secondary WAN| ONU

        %% ==================================================
        %% Segmented Zones (Proxmox Bridges)
        %% ==================================================
        subgraph Bridges ["Proxmox Internal Bridges (OpenWrt VM Segments)"]
            direction TB
            
            %% Safe Internal
            subgraph ZoneSafe ["Safe Zone (vmbr1 - Not Exposed to Internet)"]
                NG_Safe["Nginx Safe + Tailscale + CF DNS (Gray Proxy)"]
                Z["Central Database (PostgreSQL/Redis)"]
                NG_Safe --> Z
                NG_Safe --> n8n["n8n Automation"]
                NG_Safe --> Gitea["Gitea"]
                NG_Safe --> Immich["Immich"]
                NG_Safe --> NAS["HDD NAS / FileBrowser"]
                NG_Safe --> Bookstack["Bookstack"]
                NG_Safe --> Kiwix["Kiwix (Offline ZIM)"]
                NG_Safe --> Jellyfin["Jellyfin / Plex"]
            end

            %% Safe Public
            subgraph ZonePublicSafe ["Safe Public Zone (Cloudflare Tunnel - Orange Proxy)"]
                NG_Pub["Nginx Public + CF Tunnel"]
                NG_Pub --> Vaultwarden["Vaultwarden"]
                NG_Pub --> Headscale["Headscale Control Plane"]
                NG_Pub --> DB_Backup["DB Backup (Neon / Supabase)"]
                NG_Pub --> Mail["Self-Hosted Mail"]
                NG_Pub --> Telegram["Telegram Bots & Webhooks"]
            end

            %% IoT / Home Assistant
            subgraph ZoneHA ["Home Assistant Zone (Dedicated Bridge / VLAN)"]
                HA["Home Assistant Core & Integrations<br/>Native Tailscale"]
            end

            %% Unsafe / DMZ
            subgraph ZoneUnsafe ["Unsafe Zone (Tor / Torrent / Ingress)"]
                NG_Unsafe["Isolated Gateway"]
                NG_Unsafe --> Tor["Tor Node (obfs4)"]
                NG_Unsafe --> ArrStack["*Arr Stack & qBittorrent"]
                NG_Unsafe --> MQTT["Public MQTT Broker"]
            end

            subgraph ZoneDMZ ["VoIP DMZ (Fail2ban Isolated)"]
                Asterisk["Asterisk / FreePBX (VoIP / VoWiFi)"]
            end
        end

        N --> ZoneSafe
        N --> ZonePublicSafe
        N --> ZoneHA
        N --> ZoneUnsafe
        N --> ZoneDMZ
    end
```

---

## 📂 Active Projects & Experiments

### 0. Proxmox Hypervisor Host Operations
- **Directory:** `projects/00-proxmox-host/`
- **Documentation:** [[lab/projects/00-proxmox-host/runbook|Proxmox Host Operations Runbook]]
- **Covers:** Lid-close sleep masking, power schedule (12:00 AM shut down / 7:00 AM wake via RTC), low-battery protection (<40%), terminal broadcast warnings, and bridge network layouts.

### 1. Dual OpenWrt Routing & Dynamic Failover
- **Directory:** `projects/01-dual-openwrt-routing/`
- **Current Live Status:** Succeeded & Verified
- **Experiments:**
  - [[001-failover-wan|EXP-001: Dual OpenWrt WAN Failover with Metric Switching]] *(SUCCEEDED)*
  - [[002-vlan-trunking|EXP-002: Single-Cable VLAN Trunking & Multi-Mode Dual PPPoE]] *(SUCCEEDED)*
- **Runbook:** [[lab/projects/01-dual-openwrt-routing/runbook|Routing Operations & wan-mode Runbook]]

### 2. Per-Zone Nginx Reverse Proxies & WAN Dashboard
- **Directory:** `projects/02-per-zone-nginx-proxies/`
- **Documentation:** [[lab/projects/02-per-zone-nginx-proxies/README|Per-Zone Nginx Reverse Proxy Architecture]]
- **Current Component:** `nginx-home` (LXC 200, `192.168.1.130`) hosting the WAN Controller WebUI dashboard.

### 3. Vaultwarden Production Service & Monetization
- **Directory:** `projects/03-vaultwarden-service/`
- **Documentation:** [[lab/projects/03-vaultwarden-service/README|Vaultwarden Production Architecture & Monetization Blueprint]]
- **Covers:** Ingress topology, Bangladesh-only GeoIP fencing, `/admin` lockdown to 404, HTTP security headers, and the bKash/Nagad pay-to-invite onboarding workflow.

### 4. Monetized OpenWrt Captive Portal & Wi-Fi Billing
- **Directory:** `projects/04-monetized-captive-portal/`
- **Documentation:** [[lab/projects/04-monetized-captive-portal/README|Monetized OpenWrt Captive Portal & Wi-Fi Billing Architecture]]
- **Covers:** Automated Wi-Fi monetization, openNDS/CoovaChilli engines, voucher billing, bKash/Nagad integration, and session quotas.

### 5. OpenWrt Simple Local Web UI
- **Directory:** `projects/05-openwrt-simple-webui/`
- **Documentation:** [[lab/projects/05-openwrt-simple-webui/README|OpenWrt Simple Web UI Architecture & Spec]]
- **Covers:** Offline-first SPA under 200KB, ubus/JSON-RPC, wizard setup, device access lists, parental control, and 60-second safety auto-rollback engine.

### 6. OpenWrt Telegram Remote Control Bot
- **Directory:** `projects/06-openwrt-telegram-bot/`
- **Documentation:** [[lab/projects/06-openwrt-telegram-bot/README|OpenWrt Telegram Remote Control Bot Architecture & Spec]]
- **Covers:** Safe remote commands, PPPoE/reset protection boundary, unknown station join alerts with [Allow] button, numeric ID allowlist, and off-router prototype vs on-router deployment.
