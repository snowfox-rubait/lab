# 📐 Homelab Architecture Design Records (ADR)

> **Purpose:** Permanent log documenting high-level architectural decisions, network topology evolutions, security model shifts, and service isolation rationale.

---

## 📑 ADR Index
- [[#ADR-001 Master Topology Refinement and Ingress Egress Realignment]] *(2026-10-23)*
- [[#ADR-002 Fail-Safe Mode 1 Shutdown, Storage Bind Mounts, and Management Bots Zone]] *(2026-10-23)*
- [[#ADR-003 Isolated Low-Power IoT Wireless Tier, MAC Allowlisting, and MQTT Telemetry Routing]] *(2026-10-23)*
- [[#ADR-004 Live Node Zone Realignment, WAN Metric Priority, and Zero-Drift Standardization]] *(2026-10-23)*
- [[#ADR-005 Out-of-Band Pi-hole DNS Sinkhole and Strict Fallback Parental Controls]] *(2026-10-24)*
- [[#ADR-006 Dedicated Database Tier vmbr7 and Zero-Trust Inter-Bridge Firewall Hardening]] *(2026-10-24)*

---

## ADR-004: Live Node Zone Realignment, WAN Metric Priority, and Zero-Drift Standardization

- **Date:** 2026-10-23
- **Status:** Approved & Implemented
- **Scope:** Live OpenWrt VM zone interface renaming, WAN masquerading, routing metric prioritization, Proxmox host bridge provisioning (`vmbr4`–`vmbr6`), and LXC 200 metadata unification.

---

### 1. Context & Problem Statement
Following the architecture redesign in ADR-001 through ADR-003, a comprehensive audit revealed operational configuration drift between the repository blueprints and the live node states:
1. **Legacy Interface Labels on VM 100:** OpenWrt VM still utilized early prototype interface names (`safe`, `unsafe`, `notsure`) across `/etc/config/network`, `dhcp`, and `firewall`.
2. **Missing WAN Masquerading in Mode 2:** The OpenWrt firewall `zone wan` only included `wan_fiber`, meaning traffic routed through `wan_vlan` (Mode 2) did not receive proper outbound NAT masquerading.
3. **Ambiguous Default Route Priority:** Both `wan_fiber` (USB swing WAN) and `wan_vlan` (802.1Q trunk WAN) were assigned identical metric `10`, causing routing race conditions when both links had carrier.
4. **Dangerous Legacy Firewall Hole:** An unneeded rule `Allow-Admin-WAN` left over from early initial testing exposed LuCI (80, 443) and Dropbear SSH (22) directly to the public internet.
5. **Unprovisioned Bridges on Hypervisor:** Proxmox host `/etc/network/interfaces` only defined `vmbr0`–`vmbr3`, leaving `vmbr4` (Unsafe Online), `vmbr5` (DMZ), and `vmbr6` (Bots) uncreated in the kernel.
6. **Container Metadata Discrepancy:** LXC 200 was named `nginx-home` in Proxmox metadata despite its internal hostname and function being `wan-controller`.

---

### 2. Architectural Decisions & Implementations

#### 2.1 OpenWrt VM Zone Renaming & Firewall Sync
- **Action:** Executed unified renaming across UCI subsystems on VM 100:
  - `safe` $\rightarrow$ `safe_internal` (`eth1` / `10.10.10.1/24`)
  - `unsafe` $\rightarrow$ `public_ingress` (`eth2` / `10.20.20.1/24`)
  - `notsure` $\rightarrow$ `ha_iot` (`eth3` / `10.30.30.1/24`)
- **Firewall Realignment:**
  - Added `wan_vlan` to `firewall.@zone[1].network` alongside `wan_fiber`.
  - Added outbound forwarding rule from `public_ingress` to `wan` to permit Cloudflare Tunnel edge connections.
  - Deleted legacy `Allow-Admin-WAN` rule, completely closing router admin ports to public WAN interfaces.

#### 2.2 WAN Route Metric Prioritization
- **Action:** Explicitly differentiated kernel routing metrics in `/etc/config/network`:
  - `network.wan_vlan.metric='10'` (Primary inter-router trunk WAN dialer)
  - `network.wan_fiber.metric='15'` (Secondary USB swing WAN dialer)
- **Result:** Prevents default route flapping and guarantees deterministic traffic forwarding when both WAN links are active (Mode 3).

#### 2.3 Proxmox Host Bridge Provisioning
- **Action:** Added `vmbr4`, `vmbr5`, and `vmbr6` to `/etc/network/interfaces` on Proxmox host and executed `ifreload -a`.
- **Result:** All 6 virtual bridges (`vmbr1` through `vmbr6`) plus `vmbr100` are active in the Linux kernel and ready for container attachment.

#### 2.4 LXC 200 Container & DNS Alignment
- **Action:** Synchronized Proxmox metadata via `pct set 200 -hostname wan-controller` and created a static DHCP host reservation on the physical Archer C6 router (`MAC_LXC_WAN_CONTROLLER` from `.env` ➔ `192.168.1.130`, `wan-controller.lan`).

---

### 3. Consequences & Impact
- Zero drift between live system state and documentation repository.
- Mode 2 WAN failover and fail-back functions reliably with proper outbound NAT masquerading.
- Router management interfaces are fully protected from public WAN exposure.

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
- **Decision:** Selected and implemented **Option A (802.1Q VLAN 30 Trunking)** over Option B (L3 routing):
  - Extends the single-cable trunk architecture proven in [[002-vlan-trunking|EXP-002]] and fully specified in [[003-iot-vlan30-trunking|EXP-003]].
  - Sub-interface `lan3.30` on Archer C6 is combined with the `snowfox-iot` VAP in a zero-IP Layer-2 bridge (`br-iot`).
  - Proxmox bridges `enp12s0.30` into `vmbr3`.
  - OpenWrt VM serves DHCP leases in `10.30.30.0/24` with static leases for `MAC_ESP32` (`10.30.30.10`) and `MAC_ESP8266` (`10.30.30.11`).
  - OpenWrt VM firewall strictly confines IoT devices to Mosquitto MQTT (`10.30.30.2:1883`), dropping all traffic toward other internal zones and the public WAN.

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
- **Decision:** Updated `/usr/local/bin/power-manager.sh` on Proxmox to execute `revert_wan_mode` (`curl -s -m 8 -X POST "http://192.168.1.130/api/set" -H "Content-Type: application/json" -d '{"mode":"1"}'`) before all `shutdown` calls.
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
- **Original Concept:** The physical router applies default content and time restrictions across the wireless network (affecting guest and parents' repeater devices), while authorized devices (Main PC, Phone, Laptop) are placed on an explicit Layer-2 MAC allowlist.
- **Evolution & Implementation (ADR-005):** Fully designed, implemented, and verified in [[#ADR-005 Out-of-Band Pi-hole DNS Sinkhole and Strict Fallback Parental Controls|ADR-005]] and [[../projects/07-pihole-dns-sinkhole/README|Project 07: Pi-hole Out-of-Band DNS Sinkhole]].
- **Operational Policy:**
  - *Universal Baseline:* 100% of devices across the home (both allowlisted personal devices and family/guest devices) are bound to a strict baseline: **zero adult/NSFW content, zero adware/trackers, zero known malicious domains**.
  - *Tier Separation:* Allowlisted devices (`mac_allowlist`) are maintained as a distinct group in the Pi-hole database (Group 1) and are exempt from firewall anti-bypass port 53 redirection.
  - *Future Restrictions:* When custom restrictions (e.g. night-time curfews, bandwidth throttling, app blocking) are defined later, they layer directly onto the existing non-allowlisted tier without architecture changes.

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

---

## ADR-005: Out-of-Band Pi-hole DNS Sinkhole and Strict Fallback Parental Controls

- **Date:** 2026-10-24
- **Status:** Approved & Implemented
- **Scope:** Out-of-Band Pi-hole deployment (LXC 205), Archer C6 strict-order upstream DNS failover, OpenWrt fw4 (nftables) MAC allowlisting, port 53 anti-bypass redirection, port 853 DoT rejection, and multi-tier group filtering.

---

### 1. Context & Problem Statement
Enforcing parental controls, adult website blocking, and ad/malware filtering across the physical home Wi-Fi network presented several key constraints:
1. **Physical Router Hardware Limitations:** The TP-Link Archer C6 v3 gateway has only 16MB flash and 128MB RAM. Running on-router DNS blocklists (e.g., `adblock-fast` or `simple-adblock`) rapidly exhausts system RAM, causing memory pressure and triggering MediaTek MT7603E wireless driver kernel lockups.
2. **Nightly Proxmox Power-Down Window:** Per [[#ADR-002 Fail-Safe Mode 1 Shutdown, Storage Bind Mounts, and Management Bots Zone|ADR-002]], the Proxmox hypervisor automatically shuts down between 00:00 (midnight) and 07:00 AM to conserve power and battery health. If DNS is solely hosted inside a hypervisor container, all home internet resolution dies when the server powers off.
3. **Client OS DNS Fallback Quirks:** Modern client operating systems (Android, iOS, Windows) do not treat multiple DHCP-advertised DNS servers as strict primary/secondary. Instead, they query both in parallel or round-robin, leaking unblocked queries if any unfiltered secondary DNS is advertised directly via DHCP.
4. **Bypass Vectors on Client Devices:** Non-allowlisted devices (such as guest phones or repeater clients) can easily bypass DNS-based parental controls by manually configuring static DNS (e.g., `8.8.8.8` or `1.1.1.1`) in their Wi-Fi adapter settings, or by enabling Android "Private DNS" (DNS-over-TLS on port 853).

---

### 2. Architectural Decisions & Implementation

#### 2.1 Out-of-Band Pi-hole Deployment (LXC 205 on `vmbr0`)
- **Container Architecture:** Provisioned Debian 12 LXC container 205 (`pihole-oob`) attached directly to the Out-of-Band Home LAN bridge (`vmbr0`) with static IP `192.168.1.135/24` (gateway `192.168.1.1`).
- **Resource Footprint:** 1 vCPU, 512MB RAM, 4GB disk, `nesting=1`, `onboot=1` (MAC mapped via `MAC_PIHOLE_OOB` in `.env`).
- **Filter Lists Applied:** Loaded StevenBlack Standard hosts (ad/malware tracking) alongside StevenBlack Unified Adult & NSFW blocklist (`https://raw.githubusercontent.com/StevenBlack/hosts/master/alternates/porn/hosts`), totaling **148,038 unique blocked domains**.

#### 2.2 Router-Centric Strict-Order DNS Hierarchy
To solve the midnight hypervisor power-down dilemma while guaranteeing strict sequential query routing:
- Clients on the Home LAN receive **only** the physical router's IP (`192.168.1.1`) via DHCP.
- The physical router's `dnsmasq` instance is configured with `strictorder '1'` and `noresolv '1'`, forwarding queries through an explicit hierarchy:
  1. `192.168.1.135` — **Primary:** Out-of-Band Pi-hole LXC 205 (Fast local sinkhole, adblocking, adult blocking).
  2. `1.1.1.3` — **Secondary (Nightly Fallback):** Cloudflare for Families (Provides automated malware and adult content blocking during Proxmox 00:00–07:00 sleep).
  3. `9.9.9.9` — **Third:** Quad9 (Malware and phishing protection).
  4. `8.8.8.8` — **Emergency Last Resort:** Google Public DNS.
- With `strictorder '1'`, `dnsmasq` sends 100% of queries to Pi-hole when online. If Pi-hole becomes unreachable, it automatically queries the next upstream server in order without leaking unfiltered requests.

#### 2.3 OpenWrt `fw4` (nftables) MAC Allowlist & Anti-Bypass Rules
Configured on the physical Archer C6 router (`/etc/config/firewall`):
1. **MAC Allowlist (`set mac_allowlist`):**
   - Populated from `.env` hardware mappings: Main PC (`$MAC_MAIN_PC`), User Phone (`$MAC_PHONE`), Laptop Wi-Fi (`$MAC_PROXMOX_WIFI`), Proxmox Host NICs (`$MAC_PROXMOX_BUILTIN`, `$MAC_PROXMOX_LEGACY`), and Infrastructure Containers (`$MAC_PIHOLE_OOB`, `$MAC_LXC_WAN_CONTROLLER`, `$MAC_OPENWRT_VM`).
2. **Transparent DNS Interception (DNAT Port 53):**
   - Any UDP or TCP port 53 packets originating from `!mac_allowlist` are intercepted and redirected directly to the local router (`192.168.1.1:53`).
   - Prevents non-allowlisted devices from manually overriding DNS in their network settings.
3. **DoT / DoQ Hard Drop (Port 853):**
   - Outbound TCP and UDP port 853 traffic originating from `!mac_allowlist` is rejected with `REJECT`.
   - Forces Android "Private DNS" and iOS encrypted DNS clients to fall back to standard DNS (port 53), which is then intercepted and filtered.

#### 2.4 Universal Protection Baseline & Group Architecture
Utilized Pi-hole v6 FTL group management in `/etc/pihole/gravity.db`:
- **Universal Baseline Policy:** All devices across the entire network—whether personal, family repeater, or guest—are bound by the strict baseline: **zero adult/NSFW content, zero adware/trackers, zero known malicious domains**.
- **Group 0 (Default):** Assigned Adlist 1 (Ads/malware) and Adlist 2 (Adult/NSFW). Queries arriving via Archer C6 (`192.168.1.1`) enter Group 0 and receive full parental filtering.
- **Group 1 (`Whitelisted-Devices`):** Assigned Adlist 1 and Adlist 2. Personal allowlisted devices (`192.168.1.197`, `192.168.1.185`, `192.168.1.153`) share the exact same strict boundaries. They are maintained as a distinct group in the database so future custom restrictions can be added per tier without schema migration.

---

### 3. Verification & Test Results
- **Direct Ad Sinkhole Test:** Querying `pagead2.googlesyndication.com` returns `0.0.0.0` (Blocked).
- **Universal Adult Filtering:** Querying `pornhub.com` via router `192.168.1.1` returns `0.0.0.0` (Blocked).
- **Universal Allowlisted Device Filtering:** Querying `pornhub.com` from PC `192.168.1.197` directly to Pi-hole returns `0.0.0.0` (Blocked).
- **Firewall Ruleset:** `fw4 check` and `nft list chain inet fw4 dstnat_lan` confirmed active anti-bypass rules in kernel.

---

## ADR-006: Dedicated Database Tier (`vmbr7` - `10.70.70.0/24`) and Zero-Trust Inter-Bridge Firewall Hardening

- **Date:** 2026-10-24
- **Status:** Approved & Implemented on Hypervisor (`vmbr7` live)
- **Scope:** Extraction of Database and DBBackup containers into a dedicated Proxmox bridge (`vmbr7`), strict directional inter-bridge firewall pinholes on OpenWrt VM, and complete lateral movement containment.

---

### 1. Context & Problem Statement
Under the initial layout defined in ADR-001, both the Central Database (`Database`) and the backup pull job (`DBBackup`) resided inside `vmbr1` (Safe Internal Zone) alongside general application services (Gitea, Immich, NAS, Kiwix, BookStack, n8n).

However, this topology introduced two security limitations:
1. **Lateral Exposure from App Vulnerabilities:** If a web-facing or complex application container on `vmbr1` (e.g. BookStack or a community Docker container) is compromised, the attacker shares the same Layer-2 broadcast domain as the Central Database hosting master credential hashes, Vaultwarden records, and administrative data.
2. **Public-to-Internal Ingress Dilution:** Vaultwarden in `vmbr2` (Public Ingress) requires database connectivity. Opening pinholes into `vmbr1` allows traffic from the public-facing edge into the primary internal storage and application zone.
3. **Database Centralization Goal:** The user requires a centralized database architecture uniting all local self-hosted databases with remote cloud cold-backups (Supabase and Neon) into a single, dedicated data protection zone.

---

### 2. Architectural Decisions & Changes Made

#### 2.1 Creation of Dedicated Database Zone (`vmbr7` - `10.70.70.0/24`)
- **Proxmox Bridge:** Provisioned `vmbr7` on Proxmox host `/etc/network/interfaces` with zero physical ports (`bridge-ports none`).
- **Core Router Interface:** Assigned subnet `10.70.70.0/24` with OpenWrt VM acting as default gateway on `10.70.70.1`.
- **Workloads Hosted in `vmbr7`:**
  - **`Database` (`10.70.70.10`):** Central multi-tenant PostgreSQL 16 & Redis container serving Gitea, Immich, Vaultwarden, n8n, and BookStack.
  - **`DBBackup` (`10.70.70.11`):** Cold-backup sync container running scheduled automated `pg_dump` of local tenant databases and encrypted pull jobs from cloud providers (**Supabase** and **Neon**).

#### 2.2 Strict Zero-Trust Inter-Bridge Firewall Policies
Configured on OpenWrt VM (`openwrt-vm`):
1. **Default Policy for `safe_database` (`vmbr7`):**
   - `input`: `REJECT`
   - `output`: `ACCEPT`
   - `forward`: `REJECT` (Complete isolation by default; all cross-zone traffic is dropped).
2. **Pinhole: Public Ingress (`vmbr2`) $\rightarrow$ Database (`vmbr7`):**
   - Source: `10.20.20.11` (Vaultwarden only)
   - Destination: `10.70.70.10:5432` (PostgreSQL)
   - Action: `ACCEPT`. All other packets from `public_ingress` to `vmbr7` or `vmbr1` are dropped.
3. **Pinhole: Safe Internal (`vmbr1`) $\rightarrow$ Database (`vmbr7`):**
   - Source: `10.10.10.0/24` (Gitea, Immich, n8n, BookStack)
   - Destination: `10.70.70.10` on ports `TCP:5432` (Postgres) and `TCP:6379` (Redis).
   - Action: `ACCEPT`.
4. **Hard Quarantine from Untrusted Zones:**
   - From `vmbr4` (Tor / P2P), `vmbr5` (DMZ VoIP/Mail), `vmbr6` (Bots), and `vmbr0` (Home LAN / Guest): **HARD REJECT / DROP**. Zero database reachability.
5. **Egress Internet Access:**
   - `Database` engine (`10.70.70.10`): **ZERO direct internet access**.
   - `DBBackup` container (`10.70.70.11`): Pinhole permitted outbound to WAN strictly for HTTPS/TLS database replication to Supabase and Neon endpoints.

---

### 3. Consequences & Impact
- **Three-Tier Architecture:** Establishes classic industry-standard 3-Tier security: Ingress Tier (`vmbr2`) $\rightarrow$ Application Tier (`vmbr1`) $\rightarrow$ Database Tier (`vmbr7`).
- **Data Protection:** A compromise in any single web application container in `vmbr1` or `vmbr2` cannot access the underlying database filesystem or intercept traffic of adjacent services.
- **Zero Drift:** Bridge `vmbr7` is active in the Proxmox kernel and synchronized across all architecture documents, runbooks, and inventory tables.

