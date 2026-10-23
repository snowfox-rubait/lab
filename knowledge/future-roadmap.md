# 💡 Homelab Ideas, Explorations & Future Roadmap

> **Purpose:** Backlog of technologies, self-hosted services, and architectural concepts of interest. As priorities shift, items from this manifest will be graduated into dedicated projects under `lab/projects/`.

---

## 🗺️ Target Network & Service Topology
*See also: [[lab/README#🗺️ Master Network & Service Architecture|Master Architecture in README]]*

```mermaid
flowchart TD
    subgraph PhysicalWAN ["Physical & Ingress Network"]
        ISP["ISP"] --> ONU["ONU"]
        ONU --> C{"Physical Router (OpenWrt Archer C6)"}
        C -->|Parental Control / Isolated| Repeater["Wi-Fi Repeater"]
        Repeater --> Dad["Dad's Phone"]
        Repeater --> Mom["Mom's Phone"]
        C --> MyPhone["My Phone"]
        C --> PC["HP EliteDesk PC"]
    end

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

        subgraph Bridges ["Proxmox Internal Bridges (OpenWrt VM Segments)"]
            direction TB
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

            subgraph ZonePublicSafe ["Safe Public Zone (Cloudflare Tunnel - Orange Proxy)"]
                NG_Pub["Nginx Public + CF Tunnel"]
                NG_Pub --> Vaultwarden["Vaultwarden"]
                NG_Pub --> Headscale["Headscale Control Plane"]
                NG_Pub --> DB_Backup["DB Backup (Neon / Supabase)"]
                NG_Pub --> Mail["Self-Hosted Mail"]
                NG_Pub --> Telegram["Telegram Bots & Webhooks"]
            end

            subgraph ZoneHA ["Home Assistant Zone (Dedicated Bridge / VLAN)"]
                HA["Home Assistant Core & Integrations<br/>Native Tailscale"]
            end

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

## 🗄️ Storage & Media Management
- **NAS & Hard Drive Management:**
  - Candidates: **File Browser** (lightweight web file manager), **OpenMediaVault (OMV)**, **TrueNAS SCALE**, **CasaOS / ZimaOS**.
  - Traditional Samba / NFS shares for local LAN media access.
- **Photo & Memory Vault:**
  - **Immich:** Self-hosted Google Photos alternative with face recognition, mobile auto-backup, and geocoding.
- **Media Automation (*Arr Stack*):**
  - **qBittorrent** (isolated in Unsafe/P2P network with VPN binding).
  - Media management automation: **Sonarr**, **Radarr**, **Prowlarr**, **Jellyfin / Plex**.

---

## 🔒 Security, Privacy & Network Services
- **Private Mesh Networking:**
  - **Headscale:** Self-hosted, open-source implementation of the Tailscale control server (eliminating reliance on third-party Tailscale coordination servers).
- **DNS Filtering & Ad-Blocking:**
  - **Pi-hole / AdGuard Home:** Network-wide telemetry and ad sinkhole integrated into OpenWrt DHCP.
- **IPv6 & Dynamic DNS (CGNAT Bypass):**
  - Leveraging public routable **IPv6 prefixes** and DDNS to bypass ISP IPv4 CGNAT where port forwarding is blocked.
- **Anonymity & Bridges:**
  - **Tor Relay / Bridge:** Running pluggable transports (**obfs4 / obfsproxy**) to assist anti-censorship routing.
- **Intrusion Prevention:**
  - **Fail2ban / CrowdSec:** Automated IP banning based on SSH authentication failures and Nginx log abuse.

---

## 🛠️ Productivity, Knowledge & DevOps
- **Workflow Automation & Orchestration:**
  - **n8n:** Self-hosted workflow automation engine (connecting webhooks, Telegram bots, Vaultwarden invite APIs, and smart home triggers).
- **Source Control & Git:**
  - **Gitea / Forgejo:** Lightweight self-hosted GitHub alternative for private repositories and automation webhooks.
- **Visual Diagramming:**
  - **Mermaid Live Editor / Server:** Self-hosted architecture flowchart and diagram renderer.
- **Offline Knowledge Archive:**
  - **Kiwix:** Self-hosted offline Wikipedia, StackOverflow, and medical wikis stored in compressed `.zim` format.
- **Documentation & Notes:**
  - **BookStack:** Structured hierarchical documentation system (Books > Chapters > Pages).

---

## ☁️ Databases & Data Protection
- **Cold-Backup Database Sync:**
  - Automated local replica container periodically pulling and verifying cold backup dumps from managed cloud databases (**Supabase** and **Neon**).
- **IoT Message Broker:**
  - **Mosquitto MQTT:** Lightweight pub/sub message broker for ESP32, ESP8266, and Arduino telemetry.

---

## 🏠 IoT, Smart Home & Telephony
- **Smart Home Automation:**
  - **Home Assistant (OS / Supervised):** Centralized local home automation hub connecting ESP32/ESP8266 microcontrollers, Zigbee, and MQTT.
- **Self-Hosted Telephony & VoIP:**
  - **Asterisk / FreePBX:** Private PBX system for SIP intercoms, internal home extensions, and VoWiFi (Voice over Wi-Fi) routing.

---

## 📊 Evaluation & Priority Tiers

| Service | Best Execution Platform | Target Network Zone | Complexity |
| :--- | :--- | :--- | :--- |
| **n8n Automation Engine** | Docker / Debian LXC | Safe Zone (`vmbr1`) | Low |
| **Mermaid Diagram Server**| Docker / Debian LXC | Safe Zone (`vmbr1`) | Low |
| **MQTT Broker (Mosquitto)**| Debian / Alpine LXC | Safe Zone (`vmbr1`) | Low |
| **DB Backup Sync (Neon/Supa)**| Python / Bash Cron LXC | Safe Zone (`vmbr1`) | Low |
| **Gitea** | Debian LXC (Docker / Binary) | Safe Zone (`vmbr1`) | Low |
| **Headscale** | Debian LXC | Safe Zone (`vmbr1`) | Medium |
| **Pi-hole** | LXC or OpenWrt Native | Home LAN (`vmbr0`) | Low |
| **IPv6 + DDNS** | OpenWrt Native | WAN / Safe Zone | Medium |
| **Fail2ban** | Host & Nginx LXC | Safe Zone (`vmbr1`) | Low |
| **Immich** | Docker LXC + GPU passthrough | Safe Zone (`vmbr1`) | Medium |
| **Home Assistant** | Dedicated Proxmox VM / LXC | Safe Zone (`vmbr1`) | Medium |
| **File Browser / NAS** | Debian LXC + Disk Passthrough| Safe Zone (`vmbr1`) | Low |
| **qBittorrent + Arr** | Docker LXC + WireGuard VPN | Not-Sure Zone (`vmbr3`)| Medium |
| **Kiwix** | Docker LXC | Safe Zone (`vmbr1`) | Low |
| **BookStack** | Docker LXC (PHP/MariaDB) | Safe Zone (`vmbr1`) | Low |
| **Tor obfs4 Bridge** | Debian LXC | Not-Sure Zone (`vmbr3`)| Medium |
| **Asterisk / FreePBX** | Dedicated VM / Debian LXC | Safe Zone (`vmbr1`) | High |
