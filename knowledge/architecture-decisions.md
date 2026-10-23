# 📐 Homelab Architecture Design Records (ADR)

> **Purpose:** Permanent log documenting high-level architectural decisions, network topology evolutions, security model shifts, and service isolation rationale.

---

## 📑 ADR Index
- [[#ADR-001 Master Topology Refinement and Ingress Egress Realignment]] *(2026-10-23)*
- [[#ADR-002 Fail-Safe Mode 1 Shutdown, Storage Bind Mounts, and Management Bots Zone]] *(2026-10-23)*
- [[#ADR-003 Isolated Low-Power IoT Wireless Tier, MAC Allowlisting, and MQTT Telemetry Routing]] *(2026-10-23)*

---

## ADR-003: Isolated Low-Power IoT Wireless Tier, MAC Allowlisting, and MQTT Telemetry Routing

- **Date:** 2026-10-23
- **Status:** Approved
- **Scope:** Physical Archer C6 wireless AP, 2.4GHz radio tuning, hardware MAC association filtering, zero-trust guest-style network isolation, and telemetry delivery to Mosquitto MQTT in `vmbr3`.

---

### 1. Context & Problem Statement
The homelab workbench includes two microcontrollers (ESP32 and ESP8266) intended for telemetry, sensor reading, and automation. Microcontroller devices operate strictly on 2.4GHz Wi-Fi, often run bare-metal or lightweight firmware lacking full TLS crypto acceleration, and are prone to firmware exploits if left unsegmented.

Key architectural risks and challenges identified:
1. **Lateral Movement:** If placed on the default home Wi-Fi (`192.168.1.0/24`), a compromised microcontroller can probe the main workstation PC, Proxmox hypervisor, and router administration portals.
2. **RF Attack Surface:** High-power Wi-Fi broadcasts far beyond the physical room/workbench, enabling remote eavesdropping or de-authentication attacks.
3. **Rogue Associations:** Relying solely on a WPA2 PSK allows any user with the password to connect rogue devices into the IoT tier.
4. **Broker Reachability:** The Mosquitto MQTT broker is designated to run in Proxmox within the isolated `vmbr3` zone (`10.30.30.0/24`). A secure, low-overhead transport path is required between physical Wi-Fi on the Archer C6 and virtual containers on Proxmox.

---

### 2. Architectural Decisions & Implementations

#### 2.1 Dedicated Low-TX 2.4GHz Wireless Tier (`snowfox-iot`)
- **Action:** Created a secondary Virtual Access Point (VAP) on the Archer C6 `radio0` (2.4GHz).
- **Settings:**
  - Dedicated SSID: `snowfox-iot` (or `Rubait_IoT`).
  - Reduced Transmission Power: Configured with low TX power (`option txpower 10` dBm / ~10mW) to constrain the RF footprint strictly to the workbench area.
  - Client Isolation: Enabled Layer-2 client isolation (`option isolate 1`), preventing connected microcontrollers from directly communicating with or scanning each other.

#### 2.2 Layer-2 Hardware MAC Allowlisting
- **Action:** Configured 802.11 MAC filtering directly at the Wi-Fi interface level:
  - Policy: `option macfilter 'allow'`
  - Allowlist: Pinned exclusively to the hardware MAC addresses of the ESP32 and ESP8266 (tracked in `.env`).
- **Result:** Any unauthorized device attempting to associate with `snowfox-iot` is dropped at the 802.11 Layer-2 association phase before DHCP or ARP are ever initiated.

#### 2.3 Zero-Trust Guest-Style Firewall Isolation
- **Action:** Bound the IoT wireless interface to a dedicated OpenWrt firewall zone (`iot`).
- **Policy:**
  - `input`: `REJECT` (Only DHCP UDP 67 and local DNS UDP 53 permitted; Dropbear SSH port 22 and LuCI HTTP/HTTPS port 80/443 strictly blocked).
  - `forward`: `REJECT` (Completely drops all traffic destined for Home LAN `192.168.1.0/24`, router management, or other service bridges).
  - Internet / WAN: Blocked by default, with optional UDP 123 NTP pinhole if local real-time clocks require time synchronization.

#### 2.4 Telemetry Routing to Mosquitto MQTT (`vmbr3`)
- **Action:** Connect physical IoT traffic to the Mosquitto broker in `vmbr3` (`10.30.30.0/24`):
  - **Primary Model (802.1Q VLAN 30 Trunking - Recommended):** Extend the single-cable trunk architecture proven in EXP-002 (`lan3.100`) by creating `lan3.30` on Archer C6 and `enp12s0.30` on Proxmox bridged into `vmbr3`. The IoT wireless interface bridges directly into `vmbr3`, placing microcontrollers on the `10.30.30.0/24` subnet where they talk directly to Mosquitto (`10.30.30.10:1883`) without NAT or routing latency.
  - **Fallback Model (L3 Routed Subnet):** Archer C6 hosts `192.168.30.0/24` locally and uses an explicit firewall pinhole forwarding TCP 1883 to OpenWrt VM (`192.168.1.129`), which routes into `vmbr3`.

---

### 3. Consequences & Impact
- **Maximum Isolation:** Microcontrollers cannot reach the home LAN, cannot access router admin panels, cannot reach the internet, and cannot inspect adjacent IoT nodes.
- **Physical Containment:** Low transmission power limits eavesdropping range.
- **Architectural Uniformity:** Direct VLAN trunking into `vmbr3` keeps all zone firewall policies centralized within OpenWrt VM.

---

## ADR-002: Fail-Safe Mode 1 Shutdown, Storage Bind Mounts, and Management Bots Zone

- **Date:** 2026-10-23
- **Status:** Approved & Implemented
- **Scope:** Host power management, zero-network shared storage for *Arr/NAS, dedicated management bots zone (`vmbr6`), and Vaultwarden admin confinement.

---

### 1. Decisions & Implementations

#### 1.1 Automated WAN Mode 1 Fallback on Proxmox Shutdown
- **Problem:** If Proxmox powers down (either due to the midnight power-schedule or battery discharging $\le 40\%$) while in Mode 2 (VM Main), the home LAN loses PPPoE connectivity until 7:00 AM.
- **Decision:** Updated `/usr/local/bin/power-manager.sh` on Proxmox to execute `revert_wan_mode` (`curl -s -m 8 "http://192.168.1.130/api/set?mode=1"`) before all `shutdown` calls.
- **Result:** Physical router always resumes active PPPoE dialing before the OpenWrt VM powers down.

#### 1.2 Storage Bind-Mount Architecture (Eliminating Network Pinholes)
- **Problem:** Torrents and indexers (`*Arr` / `qBittorrent` in `vmbr4`) need to transfer downloaded files to the NAS and notify Jellyfin in `vmbr1`. Opening Samba/NFS ports across the firewall compromises the quarantine zone.
- **Decision:** Utilize Proxmox host-level storage bind mounts (`/mnt/storage/media`).
- **Result:** Files are written and read at native filesystem speeds without any cross-zone network traffic or open firewall ports.

#### 1.3 Dedicated Management Bots Zone (`vmbr6` - `10.60.60.0/24`)
- **Problem:** Placing Telegram bots in `vmbr4` (untrusted P2P zone) or `vmbr2` (public tunnel zone) compromises their security requirements.
- **Decision:** Created dedicated bridge `vmbr6` (`10.60.60.0/24`) for administrative and automation bots. Default policy is drop toward all internal zones, with audited firewall pinholes permitted only for:
  - Destination `192.168.1.1:22` (Router SSH management bot)
  - Destination `10.20.20.11:8085` (Vaultwarden invitation API)

#### 1.4 Vaultwarden Admin Confinement
- **Decision:** Confined Vaultwarden `/admin` strictly to local administrator workstation (`192.168.1.197/32`) and Safe Zone (`10.10.10.0/24`). Tailscale, public Cloudflare tunnel, and unprivileged containers in `10.20.20.0/24` are completely blocked with hard 404 or immediate deny responses.

#### 1.5 Wi-Fi Parental Controls via MAC Allowlist
- **Decision:** The physical router applies default content and time restrictions across the entire wireless network (affecting guest and parents' repeater devices). Authorized devices (My Phone, PC, Laptop) are placed on an explicit MAC allowlist that bypasses the restriction policy.

#### 1.6 Environment Secret Sanitization
- **Decision:** Sanitized all literal Cloudflare Zone, Account, and Tunnel UUIDs as well as hardware MAC addresses into a gitignored root `.env` file, with a documented `.env.example` template committed to Git.

---

## ADR-001: Master Topology Refinement and Ingress/Egress Realignment

- **Date:** 2026-10-23
- **Status:** Approved & Implemented in `README.md`
- **Scope:** Network segmentation, bridge numbering, reverse proxy boundaries, and ingress/egress mapping across Proxmox and OpenWrt VM.

---

### 1. Context & Problem Statement
During initial lab topology planning, services were loosely categorized by "trust" without strictly mapping how each service's protocol and connection orientation (inbound reverse proxy vs. outbound polling vs. raw direct socket) actually behave in practice.

Specifically, several architectural misalignments were identified:
1. **Mail Services in HTTP Reverse Proxy:** Self-hosted mail (`Mail`) was originally placed behind Cloudflare Tunnel and an HTTP reverse proxy (`NginxPublic`). Cloudflare Tunnel does not proxy standard TCP mail protocols (`SMTP:25/587/465`, `IMAP:993`, `POP3:995`) under free/standard plans, nor does standard Nginx HTTP proxying apply to arbitrary mail exchange.
2. **Telegram Bots Behind Public Ingress:** Telegram bots (`Telegram`) were grouped with public-facing webhooks behind `NginxPublic`. However, standard Telegram bot frameworks use long-polling (`getUpdates`) making outbound HTTPS requests to `api.telegram.org`, requiring zero inbound reverse proxying or open ports.
3. **Database Pull Jobs in Public Zone:** Database cold backup sync (`DBBackup` for Neon and Supabase) was located in the public-facing zone behind an inbound Nginx proxy. In reality, this is an outbound pull job that dumps remote database records into local storage, needing strict internal isolation rather than public ingress.
4. **Ambiguous Bridge Designations:** Only `vmbr0` (Physical LAN / OOB) and `vmbr1` (Safe Zone) were concretely numbered; other service tiers were generically labeled as "dedicated bridge", creating ambiguity during Proxmox network interface configuration.
5. **Backlog Document Clutter:** The full architecture diagram was pasted into `knowledge/future-roadmap.md`, which is intended strictly as a backlog manifest, creating duplicate maintenance overhead.

---

### 2. Architectural Decisions & Changes Made

#### 2.1 Realigning Ingress & Egress Realities
- **Mail Relocation to `ZoneDMZ`:**
  - *Action:* Moved `Mail` into `ZoneDMZ - vmbr5` alongside `Asterisk / FreePBX`.
  - *Rationale:* Both Asterisk (SIP/RTP) and Mail (SMTP/IMAP) require raw, direct layer-4/protocol port handling with `Fail2ban` IP reputation enforcement, completely separate from HTTP/HTTPS web application proxies.
- **Telegram Relocation to `ZoneUnsafe`:**
  - *Action:* Removed `Telegram` from `ZonePublicSafe` and placed it in `ZoneUnsafe - vmbr4`.
  - *Rationale:* Telegram bots operate via outbound HTTPS long-polling. Placing them in `ZoneUnsafe` isolates any bot execution environment from trusted local services while providing direct NAT egress without unnecessary Nginx reverse proxy overhead.
- **DBBackup Relocation to `ZoneSafe` & Decoupling from Nginx:**
  - *Action:* Moved `DBBackup` to `ZoneSafe - vmbr1` alongside `Database`, and removed the `NginxSafe --> DBBackup` link.
  - *Rationale:* DBBackup requires no ingress. It runs as an outbound-only scheduled job pulling dumps to local disk and the central database over OpenWrt's outbound NAT route.

#### 2.2 Standardizing Proxmox Bridge Numbering
To avoid configuration drift between documentation and Proxmox `/etc/network/interfaces`, all security tiers were assigned deterministic bridge IDs:
- **`vmbr0` (`192.168.1.0/24`):** Physical Home LAN & Out-of-Band Management (PVE Host, physical router, LXC 200 WAN controller, OOB Pi-hole).
- **`vmbr1` (`10.10.10.0/24`):** Safe Internal Zone (Private LAN, Central DB, Gitea, Immich, NAS, BookStack, n8n, Kiwix, Jellyfin, gray Cloudflare DNS via Tailscale).
- **`vmbr2` (`10.20.20.0/24`):** Safe Public Zone (Cloudflare Tunnel ingress for Vaultwarden, Headscale control plane).
- **`vmbr3` (`10.30.30.0/24`):** Dedicated IoT & Home Assistant Zone (Home Assistant core & integrations, isolated from general compute).
- **`vmbr4` (`10.40.40.0/24`):** Unsafe / Ingress Online Services (Tor obfs4 node, *Arr stack, qBittorrent, public MQTT, Telegram bots).
- **`vmbr5` (`10.50.50.0/24`):** Direct Protocol Ingress DMZ (Asterisk/FreePBX VoIP, self-hosted Mail).

#### 2.3 Single Source of Truth
- **`knowledge/future-roadmap.md`:** Stripped the duplicate architecture diagram, restoring it as a clean backlog manifest of upcoming technologies and features.
- **`README.md`:** Maintained as the primary, authoritative master architecture diagram for the entire repository.

---

### 3. How It Was Verified & Implemented
1. Updated `README.md` with corrected Mermaid node linkages, removing erroneous ingress arrows and applying explicit `vmbr` bridge labels.
2. Verified Mermaid syntax compatibility in Obsidian (no raw unquoted parentheses or malformed thick arrows).
3. Cleaned `knowledge/future-roadmap.md` and verified internal markdown links.
4. Verified Git working tree and committed atomic changes to `snowfox-rubait/lab.git`.

---

### 4. Consequences & Impact
- **Clarity:** Next implementation phases (deploying LXC containers and Proxmox bridges) now have unambiguous bridge mappings and security models.
- **Security:** Inbound exposure is strictly constrained to services that genuinely require it (`ZonePublicSafe` via Cloudflare Tunnel, and `ZoneDMZ` via firewall-bounced raw ports). Trusted backup data stays strictly on internal bridges.
