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
