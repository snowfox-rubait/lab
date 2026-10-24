# 🧠 Mistakes to Avoid (Lessons Learned)

> **Purpose:** Living catalog of architectural, networking, and system configuration pitfalls encountered across our homelab experiments. Review before designing new network topologies or provisioning services.

---

### 1. Networking & Multi-Router Topologies

#### ❌ Running multiple DHCP servers on the same broadcast domain
- **Problem:** When two routers connect to the same switch or VLAN with DHCP active, clients randomly pick whoever replies first, causing split-brain routing and unstable IP assignment.
- **Rule:** Never enable DHCP on more than one device per broadcast domain. If connecting a secondary router via its LAN/uplink interface, always set `dhcp.<interface>.ignore='1'`.

#### ❌ Forgetting DNS Rebind Protection for Custom Apex Domains
- **Problem:** Resolving local IPs (e.g. `192.168.1.x`) via a public domain name like `*.snowfox.live` gets dropped by OpenWrt/dnsmasq by default due to DNS rebind protection.
- **Fix:** Always add `list rebind_domain 'snowfox.live'` in `/etc/config/dhcp`.

---

### 2. Proxmox & Virtualization

#### ❌ Relying on default systemd lid actions on laptop servers
- **Problem:** Laptops used as headless hypervisors will suspend when the lid is closed or when AC power fluctuates.
- **Fix:** Both `HandleLidSwitch=ignore` in `/etc/systemd/logind.conf.d/` AND masking `sleep.target`, `suspend.target`, `hibernate.target`, `hybrid-sleep.target` are required.

#### ❌ Binding USB devices by bus/port number instead of Vendor:Product ID
- **Problem:** If a USB Ethernet dongle or serial adapter is plugged into a different USB port, the VM fails to capture it or boots without the device.
- **Fix:** Always pass through USB by persistent vendor and product ID (`host=XXXX:YYYY`), e.g., `qm set 100 --usb0 host=35b5:3500`.

#### ❌ Hard-wiring physical interface names in bridge ports before verifying existence
- **Problem:** Adding missing network cards to `/etc/network/interfaces` bridge-ports causes `ifreload -a` to fail.
- **Fix:** Always verify present interfaces with `ip -brief link` first.

---

### 3. DNS Filtering, Sinkholes & Parental Controls

#### ❌ Advertising multiple DNS servers directly via DHCP to client devices
- **Problem:** Client operating systems (Windows, Android, iOS) do not treat DHCP-advertised DNS servers as strict primary and secondary. Instead, they query them concurrently or round-robin. If an unfiltered secondary DNS is announced via DHCP, filtered queries leak and bypass blocking entirely.
- **Fix:** Advertise **only** the local physical router's IP (`192.168.1.1`) via DHCP, and let the router manage sequential upstream forwarding (`strictorder '1'`).

#### ❌ Hosting large adblock lists natively on low-RAM embedded routers
- **Problem:** Running memory-heavy blocklists (e.g., 150k+ domains) natively on a 128MB RAM embedded router (such as Archer C6) consumes system memory, triggers kernel OOM reaper, and crashes MediaTek MT7603E wireless drivers.
- **Fix:** Offload all heavy DNS filtering to a dedicated hypervisor LXC container (Pi-hole on `vmbr0`), using the physical router strictly as a fast caching forwarder.

#### ❌ Omitting DNS anti-bypass firewall interception
- **Problem:** Tech-savvy users, guest devices, or smart TVs can bypass network-wide parental controls simply by hardcoding static DNS (`8.8.8.8` or `1.1.1.1`) in network settings or turning on Android "Private DNS" (DoT port 853).
- **Fix:** Configure `fw4` / nftables to transparently intercept port 53 (DNAT redirect to local router) and hard-reject port 853 for non-allowlisted devices.

#### ❌ Assuming port-level DNS rules provide absolute 100% prevention
- **Problem:** Port 53 DNAT and Port 853 rejection provide strong **DNS bypass resistance**, but do not stop DNS-over-HTTPS (DoH on port 443) or MAC spoofing.
- **Fix:** Block the Firefox DoH canary domain (`use-application-dns.net`), drop known DoH bootstrap IPs, and recognize that MAC allowlists are operational heuristics that require disabling MAC randomization on client devices.

---

### 4. API Design & Web Management Services

#### ❌ Exposing state-changing infrastructure APIs via unauthenticated HTTP GET
- **Problem:** Writing endpoints like `GET /api/set?mode=...` without authentication allows any device on the LAN (or an untrusted website triggering a cross-site image load `<img src="http://192.168.1.130/api/set?mode=2">`) to execute a CSRF attack and flip physical router WAN modes.
- **Fix:** State mutations must strictly require **HTTP POST**, enforce source IP allowlists (e.g. administrator workstation and hypervisor host only), and validate request payloads.

---

### 5. IP Address Planning & Subnet Allocation

#### ❌ Overlapping IP assignments between server daemons and client static leases
- **Problem:** Assigning the same IP (e.g. `10.30.30.10`) to both a central server (Mosquitto MQTT broker) and a DHCP client device (ESP32) creates an immediate ARP collision and breaks network routing.
- **Fix:** Always maintain a single authoritative IP allocation table per subnet: reserve low IPs (`.2`–`.9`) for infrastructure daemons, middle IPs (`.10`–`.49`) for static client leases, and upper blocks (`.100`–`.200`) for dynamic DHCP pools.
