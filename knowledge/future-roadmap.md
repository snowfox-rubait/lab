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
- **Deep Packet Inspection & Intrusion Prevention (DPI/IPS):**
  - **Suricata / Snort in Proxmox Container:** Host an enterprise-grade L7 packet inspection engine in a dedicated container or gateway VM to perform real-time TLS SNI inspection, signature-based malware blocking, and automated traffic blocking pipelines that exceed physical router CPU/RAM limits.
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
  - **AtelierDocs:** Self-hosted documentation and document template management system.
- **PDF Manipulation & Processing:**
  - **Stirling-PDF:** Powerful, locally hosted one-stop PDF tool (merge, split, OCR, convert, watermark, redact, sign).
  - **BentoPDF:** Privacy-first, lightweight client-side browser PDF toolkit (runs locally in browser without server processing overhead).
- **Developer & IT Utilities:**
  - **IT-Tools:** Ultralight Swiss Army knife collection of handy online developer & sysadmin utilities (token generators, converters, encoders, regex testers, cheatsheets).
  - **OmniTools:** Self-hosted developer multi-tool suite (formatters, parsers, converters, code generators).
- **Personal URL Shortener (`short.snowfox.live`):**
  - Personal branded short-link redirection service (evaluating Cloudflare Workers + KV for 24/7 edge uptime vs. self-hosted Shlink on PostgreSQL `vmbr2`). Private authenticated single-user generation, public friction-free redirection. (See [Project 13](../projects/13-personal-url-shortener/README.md)).

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

The baseline infrastructure is live under [07-pihole-dns-sinkhole](../projects/07-pihole-dns-sinkhole/README.md) and [ADR-005](architecture-decisions.md#adr-005-out-of-band-pi-hole-dns-sinkhole-and-strict-fallback-parental-controls). The following future restriction vectors are cataloged for upcoming implementation:

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
   - *Mechanism:* Convergence with [04-monetized-captive-portal](../projects/04-monetized-captive-portal/README.md) for time-limited session tokens.

---

## 📊 Evaluation & Priority Tiers

| Service | Best Execution Platform | Target Network Zone | Complexity |
| :--- | :--- | :--- | :--- |
| **Pi-hole DNS Sinkhole** | Debian 12 LXC (LXC 205) | Home LAN / OOB (`vmbr0`) | 🟢 **Graduated to Live (`07-pihole`)** |
| **Multi-WAN Load Balancing (`mwan3`)** | Archer C6 & OpenWrt VM | Home LAN (`vmbr0` / VLAN 100) | 🟡 **Staged (`11-multiwan`)** |
| **Central Database (PostgreSQL 17 / Redis 7)**| Debian 13 LXC (LXC 210) | Dedicated Database (`vmbr7`) | 🟢 **Live (`12-central-database`)** |
| **Vaultwarden Production** | Docker in Debian 13 LXC (LXC 220) | Public Ingress (`vmbr2`) | 🟢 **Live (`03-vaultwarden`)** |
| **Public Reverse Proxy (`nginx-public`)** | Debian 13 LXC (LXC 202) | Public Ingress (`vmbr2`) | 🟢 **Live (`02-per-zone-nginx`)** |
| **Fail2ban Intrusion Defense** | Native Proxmox Host | Proxmox Management (`:8006`, `:22`) | 🟢 **Live (`knowledge/security-fail2ban`)** |
| **n8n Automation Engine** | Debian 13 LXC | Safe Internal (`vmbr1`) | High (`08-n8n`) |
| **Gitea Source Control** | Debian 13 LXC | Safe Internal (`vmbr1`) | High |
| **Centralized Telegram Hub** | Debian 13 LXC | Safe Internal / OOB (`vmbr0`) | Low (`09-telegram`) |
| **Workstation AV / EDR Stack** | Native Linux (EliteDesk PC) | Workstation Host (`rubait`) | Medium (`10-workstation-av`) |
| **Mermaid Diagram Server**| Docker / Debian 13 LXC | Safe Internal (`vmbr1`) | Low |
| **DB Backup Sync (Neon/Supa)**| Debian 13 LXC | Dedicated Database (`vmbr7`) | Low |
| **Immich Photo Vault** | Docker in Debian 13 LXC | Safe Internal (`vmbr1`) | Medium |
| **File Browser / NAS** | Debian 13 LXC + Disk Passthrough| Safe Internal (`vmbr1`) | Low |
| **Kiwix (Offline ZIM)** | Debian 13 LXC | Safe Internal (`vmbr1`) | Low |
| **BookStack** | Debian 13 LXC | Safe Internal (`vmbr1`) | Low |
| **AtelierDocs** | Docker / Node LXC | Safe Internal (`vmbr1`) | Low |
| **Stirling-PDF** | Docker in Debian 13 LXC | Safe Internal (`vmbr1`) | Low |
| **BentoPDF** | Static Web / Docker LXC | Safe Internal (`vmbr1`) | Low |
| **IT-Tools** | Docker in Debian 13 LXC | Safe Internal (`vmbr1`) | Low |
| **OmniTools** | Docker in Debian 13 LXC | Safe Internal (`vmbr1`) | Low |
| **Personal URL Shortener (`short.snowfox.live`)** | Cloudflare Worker / LXC | Cloudflare Edge / Public Ingress (`vmbr2`) | Low (`13-personal-url-shortener`) |
| **Headscale** | *Undecided / Separated* | *Deferred (Out of current scope)* | Medium |
| **Home Assistant Core** | Dedicated Proxmox VM / LXC | Home Assistant & IoT (`vmbr3`) | Medium |
| **MQTT Broker (Mosquitto)**| Debian 13 LXC | Home Assistant & IoT (`vmbr3`) | Low |
| **qBittorrent + *Arr Stack** | Docker LXC + VPN + Host Mount | Unsafe Online (`vmbr4`)| Medium |
| **Suricata / Snort DPI Container** | Debian 13 LXC / Inline VM | Gateway Inspection Tier | Low (Future Architecture) |
| **Asterisk / FreePBX** | Dedicated VM / Debian LXC | Protocol DMZ (`vmbr5`) | High |
| **Self-Hosted Mail** | Debian 13 LXC (Postfix/Dovecot) | Protocol DMZ (`vmbr5`) | High |
| **Router & Onboarding Bots** | Python in Debian 13 LXC | Management Bots (`vmbr6`) | Low |
