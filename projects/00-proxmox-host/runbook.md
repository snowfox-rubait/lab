# 💻 Proxmox Hypervisor Host Operations Runbook

> **Target Node:** ThinkPad Laptop (Intel Core i5 3rd Gen)  
> **Management IP:** `192.168.1.2` (`ssh proxmox`)  
> **Hypervisor OS:** Proxmox VE / Debian Linux

---

## 📦 APT Package Repositories (No-Subscription)

Proxmox VE by default ships with enterprise repositories enabled (`pve-enterprise.sources` and `ceph.sources`), which throw 401 Unauthorized errors without a paid subscription key.

### Configuration Applied:
1. **Disabled Enterprise Sources:**
   - `/etc/apt/sources.list.d/pve-enterprise.sources` -> `.disabled`
   - `/etc/apt/sources.list.d/ceph.sources` -> `.disabled`
2. **Enabled Free Community Repositories (Debian Trixie / PVE 9):**
   - **`/etc/apt/sources.list.d/pve-no-subscription.sources`**:
     ```deb822
     Types: deb
     URIs: http://download.proxmox.com/debian/pve
     Suites: trixie
     Components: pve-no-subscription
     Signed-By: /usr/share/keyrings/proxmox-archive-keyring.gpg
     ```
   - **`/etc/apt/sources.list.d/ceph-no-subscription.sources`**:
     ```deb822
     Types: deb
     URIs: http://download.proxmox.com/debian/ceph-squid
     Suites: trixie
     Components: no-subscription
     Signed-By: /usr/share/keyrings/proxmox-archive-keyring.gpg
     ```
3. **Verification:**
   - Executed `apt update` with 100% success; package index synced cleanly.

---

## 🚀 Virtual Router VM 100 (OpenWrt) Upgrade
- Upgraded in-place via `sysupgrade -v -k` from OpenWrt `23.05.5` to **`OpenWrt 25.12.6`** (Linux kernel 6.12.112), matching the physical router.
- Switched package manager workflow from legacy `opkg` to modern **`apk`**.
- Reinstalled USB Ethernet driver via `apk add kmod-usb-net-cdc-ether` and `usbutils`.

---

## ⚡ Power & Thermal Management

### 1. Lid-Close Sleep Prevention
Because this server is a laptop running with the lid closed, standard Linux power management would suspend the CPU upon lid closure or AC power disconnect.
- **Config file:** `/etc/systemd/logind.conf.d/ignore-lid.conf`
  ```ini
  [Login]
  HandleLidSwitch=ignore
  HandleLidSwitchExternalPower=ignore
  HandleLidSwitchDocked=ignore
  ```
- **Masked systemd targets:**
  - `sleep.target`
  - `suspend.target`
  - `hibernate.target`
  - `hybrid-sleep.target`

---

## 🌙 Automated Nightly Schedule & Battery Protection

Managed by `/usr/local/bin/power-manager.sh` and `/etc/cron.d/power-manager` (tracked in repo under [scripts/power-manager.sh](scripts/power-manager.sh) and [services/power-manager.cron](services/power-manager.cron)).

### Rules Configured:
1. **Low Battery Auto-Shutdown (< 40% and Discharging):**
   - Polled every 2 minutes via cron.
   - If AC is unplugged/discharging and battery drops to $\le 40\%$:
     - Broadcasts warning to all active terminal sessions via `wall`.
     - Initiates safe shutdown in 2 minutes (`shutdown -h +2`).
2. **Nightly Schedule (12:00 AM Shutdown, 7:00 AM Auto-Wake):**
   - At 00:00 (Midnight), calculates epoch timestamp for `07:00:00 AM`.
   - Programs the hardware RTC alarm using `/usr/sbin/rtcwake -m no -t <timestamp>`.
3. **Mid-Session Warning (SSH Active):**
   - Uses Linux `wall` (write all) to broadcast an urgent banner directly across every active PTS/SSH terminal.
   - If an active SSH session is detected:
     - Warning: *"NIGHTLY SHUTDOWN NOTICE: It is 12:00 AM. Server shutdown scheduled with RTC wake at 7:00 AM in 10 minutes. Run 'shutdown -c' to cancel."*
     - Delays shutdown by 10 minutes giving the user time to finish work or abort via `shutdown -c`.
   - If no active SSH sessions:
     - Initiates shutdown in 2 minutes.

---

## 🌉 Network Bridges Layout

| Bridge  | Attached Physical Port   | Subnet / Role                                                  |
| :------ | :----------------------- | :------------------------------------------------------------- |
| `vmbr0` | `enp12s0` (Built-in NIC) | Home LAN / Out-of-Band Management (`192.168.1.0/24`)           |
| `vmbr1` | *None (isolated)*        | Safe Internal Zone (`10.10.10.0/24`)                           |
| `vmbr2` | *None (isolated)*        | Safe Public Ingress Zone (`10.20.20.0/24`)                     |
| `vmbr3` | `enp12s0.30`             | Home Assistant & IoT Zone (`10.30.30.0/24`, VLAN 30 Trunk)    |
| `vmbr4` | *None (isolated)*        | Unsafe / Online Workloads Zone (`10.40.40.0/24`)               |
| `vmbr5` | *None (isolated)*        | Direct Protocol Ingress DMZ (`10.50.50.0/24`)                  |
| `vmbr6` | *None (isolated)*        | Management & Telegram Bots Zone (`10.60.60.0/24`)              |
| `vmbr7` | *None (isolated)*        | Dedicated Database & Data Protection Tier (`10.70.70.0/24`)    |
| `vmbr100` | `enp12s0.100`          | Dedicated WAN VLAN Trunk Bridge (VLAN 100 for VM PPPoE dialer) |

---

## 🔌 Hardware Passthrough
- **Device:** Naxiang SZNX LAN 100M USB Adapter
- **Hardware ID:** `35b5:3500`
- **Assigned to:** VM 100 (OpenWrt) via `qm set 100 --usb0 host=35b5:3500` (soft non-blocking dependency).

---

## ⚡ Wake-on-LAN (WOL) Configuration

Linux network drivers frequently disable Wake-on-LAN by default (`Wake-on: d`).
To enable waking the laptop over Ethernet:

- **Interface:** `enp12s0` (Physical MAC: `b8:88:e3:e7:5e:1f`)
- **Mode:** Magic Packet (`g`)
- **Systemd Service:** `/etc/systemd/system/wol.service` (Ensures `ethtool -s enp12s0 wol g` is set on every system boot).
- **Trigger Command from Workstation PC:**
  ```bash
  wake-proxmox
  ```
  *(Sends broadcast magic packet across LAN and triggers router `etherwake` directly)*
- **Trigger Command from Router:**
  ```bash
  /usr/bin/wake-proxmox
  # or direct command:
  /usr/bin/etherwake -D -i br-lan b8:88:e3:e7:5e:1f
  ```

---

## ⏰ Dual-Redundant 7:00 AM Auto-Wake Architecture

### Why `rtcwake` alone can fail on laptops:
1. Standard laptop motherboards cut power to the Super I/O / RTC wake pin in mechanical ACPI S5 (Poweroff). Many consumer/ThinkPad laptop chipsets only support RTC wake from **S3 (Suspend to RAM) / S4 (Hibernate)**, not from hard S5 `shutdown -h`.
2. When the kernel powers off via ACPI, the motherboard chipset can clear the pending `wakealarm` register unless suspended.

### Solution: Router-Driven Wake-on-LAN + RTC Dual Wake
To guarantee the laptop wakes up at 7:00 AM regardless of motherboard S5 power state:
- **Primary Wake Engine (Physical Router OpenWrt):**
  The Archer C6 router is always on (24/7). A cron job triggers at 7:00 AM sharp to send a Wake-on-LAN Magic Packet:
  ```cron
  0 7 * * * /usr/bin/etherwake -i br-lan b8:88:e3:e7:5e:1f
  ```
- **Secondary Wake Engine (Host `rtcwake`):**
  Sets the hardware RTC alarm at midnight shutdown as an internal fallback.

### On-Demand Wake-on-LAN & Cold-Boot Latency
When the hypervisor is offline or sleeping, it can be awakened on-demand at any time:
```bash
# From Workstation PC (local script broadcasts LAN packet & calls router switch):
wake-proxmox

# Directly from the physical OpenWrt router:
ssh router "/usr/bin/wake-proxmox"
# Or raw etherwake:
ssh router "/usr/bin/etherwake -D -i br-lan b8:88:e3:e7:5e:1f"
```

> [!IMPORTANT]
> **Boot Latency Notice (1 to 2 Minutes):**  
> After sending the WoL magic packet, laptop hardware requires 30–45 seconds for motherboard BIOS POST, followed by Linux kernel loading and sequential guest initialization. Even after host SSH responds, allow **1 to 2 minutes** for OpenWrt VM 100, `db-central` (LXC 210), and `vaultwarden` (LXC 220) to reach full network and database convergence before accessing services.

---

## ⏱️ VM & LXC Startup Sequencing (`order=X,up=Y`)

To eliminate startup race conditions (where applications crash because their gateway or central database is not yet listening), strict startup priorities and delays are configured across Proxmox guests:

| Order | Guest ID | Hostname | Type | Delay (`up`) | Role & Dependency Rationale |
| :---: | :---: | :--- | :---: | :---: | :--- |
| **1** | `100` | `openwrt` | VM | `15s` | **Core Virtual Router:** Must boot first to initialize `vmbr1`–`vmbr7` routing, NAT, and gateway `10.70.70.1`. |
| **2** | `210` | `db-central` | LXC | `10s` | **Central Database Tier:** Starts PostgreSQL 17.11 & Redis 7 so database sockets are ready for tenants. |
| **3** | `220` | `vaultwarden` | LXC | `5s` | **Core Application:** Connects to PostgreSQL over `vmbr7` pinhole. Starts before reverse proxy. |
| **4** | `202` | `nginx-public` | LXC | `5s` | **Public Ingress:** Starts Nginx reverse proxy and `cloudflared` tunnel daemon. |
| **5** | `205` | `pihole-oob` | LXC | `0s` | **DNS Sinkhole:** Starts out-of-band DNS filtering on `vmbr0`. |
| **6** | `200` | `wan-controller`| LXC | `0s` | **Management Scripts:** Lightweight Python/Nginx failover API. |

For deep post-mortem analysis of startup timing, masquerade edge cases, and historical fixes, refer to [troubleshooting-and-post-mortem.md](troubleshooting-and-post-mortem.md).

---

## 📱 Mobile Device Wi-Fi MAC Randomization Notice
> [!IMPORTANT]
> Modern Android (10+) and iOS (14+) enable **MAC Address Randomization** by default per SSID.
> If a client device connects with a randomized MAC, it will not match the physical router's MAC allowlist and will automatically fall into the restricted parental control policy.
> - **Required Device Setting for Allowlist Exemption:**
>   - Android: `Settings` $\rightarrow$ `Wi-Fi` $\rightarrow$ `[Home Network]` $\rightarrow$ `Privacy` $\rightarrow$ Select **"Use device MAC"**.
>   - iOS: `Settings` $\rightarrow$ `Wi-Fi` $\rightarrow$ `(i)` next to network $\rightarrow$ Toggle **"Private Wi-Fi Address"** to **Off**.

---

## 🛡️ Out-of-Band Pi-hole DNS Sinkhole (LXC 205: `pihole-oob`)

> **Dedicated Project Documentation:** [07-pihole-dns-sinkhole](../07-pihole-dns-sinkhole/README.md)  
> **Operations Runbook:** [Pi-hole Runbook](../07-pihole-dns-sinkhole/runbook.md)

To provide network-wide parental controls, adult website blocking, and ad filtering without overloading the physical router's limited RAM/flash, a dedicated Pi-hole instance runs directly on the Out-of-Band management bridge (`vmbr0`).

### Container Specifications:
- **Container ID:** `205` (`pihole-oob`)
- **Base OS:** Debian 12 (Bookworm)
- **Network Interface:** `eth0` bridged to `vmbr0`
- **Static IP:** `192.168.1.135/24` (Gateway: `192.168.1.1`)
- **Hardware MAC:** Mapped via `MAC_PIHOLE_OOB` in `.env`
- **Resources:** 1 vCPU, 512MB RAM, 4GB Storage (`nesting=1`, `onboot=1`)
- **Web Admin Interface:** `http://192.168.1.135/admin`
- **Software Stack:** Pi-hole Core v6.5, Web v6.6.1, FTL v6.8

### Blocklists & Group Segmentation:
- **Gravity Database:** `/etc/pihole/gravity.db`
- **Adlists Configured:**
  - **Adlist 1:** StevenBlack Standard (`https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts`) — Adware, malware, and telemetry tracking.
  - **Adlist 2:** StevenBlack Unified Adult & NSFW (`https://raw.githubusercontent.com/StevenBlack/hosts/master/alternates/porn/hosts`) — Adult, pornographic, and explicit domains (**148,038 unique domains**).
- **Group Mappings:**
  - **Group 0 (`Default`):** Contains Adlist 1 + Adlist 2. All traffic forwarded from the physical router (`192.168.1.1`) and unmapped clients receive full ad, adult, and malware filtering.
  - **Group 1 (`Whitelisted-Devices`):** Contains Adlist 1 + Adlist 2. Personal allowlisted devices (`192.168.1.197`, `192.168.1.185`, `192.168.1.153`) share the universal baseline (no adult, no harmful sites, no ads). Kept as a discrete group in the database so custom granular policies or future restrictions can be layered on top without restructuring.

### Useful Maintenance Commands:
```bash
# Check Pi-hole service status inside LXC 205:
ssh proxmox "pct exec 205 -- /usr/local/bin/pihole status"

# Reload gravity blocklists without restarting DNS:
ssh proxmox "pct exec 205 -- /usr/local/bin/pihole reloaddns"

# Manually trigger gravity blocklist update:
ssh proxmox "pct exec 205 -- /usr/local/bin/pihole updateGravity"

# Inspect group and client assignments in gravity database:
ssh proxmox "pct exec 205 -- sqlite3 /etc/pihole/gravity.db 'SELECT c.ip, c.comment, g.name FROM client c JOIN client_by_group cbg ON c.id=cbg.client_id JOIN \"group\" g ON cbg.group_id=g.id;'"
```

> [!NOTE]
> **Automated Gravity Updates:** Pi-hole automatically updates its ad and adult gravity database every week on Sunday morning at 04:07 UTC via `/etc/cron.d/pihole` (`7 4 * * 7 pihole ... pihole updateGravity`). Manual execution is only required when introducing new blocklist URLs.

---

## 🛡️ Host Intrusion Prevention (Fail2ban)

Proxmox VE is protected against local brute-force attacks on the Web GUI (`:8006`) and SSH (`:22`) via Fail2ban with `nftables-multiport` actions:

- **Configuration:** `/etc/fail2ban/jail.local` (Tracked in [services/jail.local](services/jail.local))
- **Active Jails:**
  - `proxmox`: Monitors `/var/log/pveproxy/access.log` (Bans IPs after 3 failed web logins for 24 hours).
  - `sshd`: Monitors systemd journal for SSH authentication failures (Aggressive mode, 24-hour ban).
- **Allowlist:** Workstation PC (`192.168.1.197`), physical router (`192.168.1.1`), and loopback are permanently exempt.
- **Terminal Telemetry Dashboard:**
  ```bash
  ssh proxmox "/usr/local/bin/fail2ban-summary"
  ```
  *(Source tracked in [scripts/fail2ban-summary](scripts/fail2ban-summary))*
- **Operational Commands:**
  ```bash
  # Check status of all jails:
  ssh proxmox "fail2ban-client status"

  # Check active bans on Proxmox Web GUI:
  ssh proxmox "fail2ban-client status proxmox"

  # Manually unban an IP:
  ssh proxmox "fail2ban-client unban <IP_ADDRESS>"
  ```

---

## 🌐 Remote Mesh Access & Tailscale Subnet Router (`pve-thinkpad`)

> **Node Name:** `pve-thinkpad`  
> **Tailscale IP:** `100.127.129.106`  
> **Mesh Ingress Service:** `/etc/systemd/system/tailscale-proxy-forward.service` (Tracked in [services/tailscale-proxy-forward.service](services/tailscale-proxy-forward.service))

Proxmox VE runs official Tailscale as a dual-purpose mesh router:
1. **Subnet Router:** Advertises internal subnets `10.10.10.0/24` (Safe Zone), `10.30.30.0/24` (IoT Zone), and `192.168.1.0/24` (Out-of-Band LAN) with `net.ipv4.ip_forward = 1` persisted in `/etc/sysctl.d/99-tailscale.conf`.
2. **Safe Zone Port Forwarding Gateway:** Transparently forwards inbound HTTP (:80) and HTTPS (:443) traffic arriving on `tailscale0` directly to `nginx-safe` (`10.10.10.10`), enabling seamless access to `pve.snowfox.live`, `short-admin.snowfox.live`, `pihole.snowfox.live`, and other private internal domains from any phone, laptop, or remote client over the tailnet without requiring client-side subnet route acceptance.

### Operational Commands:
```bash
# Check Tailscale status:
ssh proxmox "tailscale status"

# View advertised subnet routes:
ssh proxmox "tailscale debug prefs | grep -A 5 -i 'AdvertiseRoutes'"

# Check port forwarding service:
ssh proxmox "systemctl status tailscale-proxy-forward.service"
```

