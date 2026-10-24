# 💡 Homelab Ideas, Explorations & Future Roadmap

> **Purpose:** Backlog of technologies, self-hosted services, and architectural concepts of interest. As priorities shift, items from this manifest will be graduated into dedicated projects under `lab/projects/`.

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

## 🛡️ Future Parental Controls & Policy Restriction Roadmap

The baseline infrastructure is live under [[../projects/07-pihole-dns-sinkhole/README|07-pihole-dns-sinkhole]] and [[architecture-decisions#ADR-005 Out-of-Band Pi-hole DNS Sinkhole and Strict Fallback Parental Controls|ADR-005]]. The following future restriction vectors are cataloged for upcoming implementation:

1. **Time-of-Day Internet Curfew (Scheduled Lockout):**
   - *Target:* Non-allowlisted family and repeater devices.
   - *Mechanism:* OpenWrt `fw4` scheduled time rules dropping outbound WAN forwarding between 23:00 and 06:00, while leaving allowlisted management devices active.
2. **Bandwidth Throttling & SQM per Device Tier:**
   - *Target:* Non-allowlisted devices and guest repeaters.
   - *Mechanism:* Cake / fq_codel SQM queuing to prevent video streaming on secondary devices from degrading workstation or gaming latency.
3. **Application & Category-Specific Pi-hole Blocklists:**
   - *Target:* Discrete Pi-hole database groups (`gravity.db`).
   - *Mechanism:* Curated regex blocklists for social media (TikTok, Instagram, Facebook) and mobile gaming servers layered onto specific target devices.
4. **Captive Portal Voucher Integration:**
   - *Target:* Guest devices.
   - *Mechanism:* Convergence with [[../projects/04-monetized-captive-portal/README|04-monetized-captive-portal]] for time-limited session tokens.

---

## 📊 Evaluation & Priority Tiers

| Service | Best Execution Platform | Target Network Zone | Complexity |
| :--- | :--- | :--- | :--- |
| **Pi-hole DNS Sinkhole** | Debian 12 LXC (LXC 205) | Home LAN / OOB (`vmbr0`) | 🟢 **Graduated to Live (`07-pihole`)** |
| **Multi-WAN Load Balancing (`mwan3`)** | Archer C6 & OpenWrt VM | Home LAN (`vmbr0` / VLAN 100) | 🟡 **Staged (`11-multiwan`)** |
| **n8n Automation Engine** | Docker / Debian LXC | Safe Internal (`vmbr1`) | Low (`08-n8n`) |
| **Centralized Telegram Hub** | Docker / Debian LXC | Safe Internal / OOB (`vmbr0`) | Low (`09-telegram`) |
| **Workstation AV / EDR Stack** | Native Linux (EliteDesk PC) | Workstation Host (`rubait`) | Medium (`10-workstation-av`) |
| **Mermaid Diagram Server**| Docker / Debian LXC | Safe Internal (`vmbr1`) | Low |
| **Central DB (PostgreSQL)**| Debian LXC | Dedicated Database (`vmbr7`) | Medium |
| **DB Backup Sync (Neon/Supa)**| Python / Bash Cron LXC | Dedicated Database (`vmbr7`) | Low |
| **Gitea** | Debian LXC (Docker / Binary) | Safe Internal (`vmbr1`) | Low |
| **Immich** | Docker LXC + GPU passthrough | Safe Internal (`vmbr1`) | Medium |
| **File Browser / NAS** | Debian LXC + Disk Passthrough| Safe Internal (`vmbr1`) | Low |
| **Kiwix (Offline ZIM)** | Docker LXC | Safe Internal (`vmbr1`) | Low |
| **BookStack** | Docker LXC (PHP/MariaDB) | Safe Internal (`vmbr1`) | Low |
| **Vaultwarden** | Docker in Debian 13 LXC | Public Ingress (`vmbr2`) | 🟢 **Live (`03-vaultwarden`)** |
| **Headscale** | *Undecided / Separated* | *Deferred (Out of current scope)* | Medium |
| **Home Assistant Core** | Dedicated Proxmox VM / LXC | Home Assistant & IoT (`vmbr3`) | Medium |
| **MQTT Broker (Mosquitto)**| Debian / Alpine LXC | Home Assistant & IoT (`vmbr3`) | Low |
| **qBittorrent + *Arr Stack** | Docker LXC + VPN + Host Mount | Unsafe Online (`vmbr4`)| Medium |
| **Tor obfs4 Bridge** | Debian LXC | Unsafe Online (`vmbr4`)| Medium |
| **Asterisk / FreePBX** | Dedicated VM / Debian LXC | Protocol DMZ (`vmbr5`) | High |
| **Self-Hosted Mail** | Debian LXC (Postfix/Dovecot) | Protocol DMZ (`vmbr5`) | High |
| **Router & Onboarding Bots** | Python LXC | Management Bots (`vmbr6`) | Low |
