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

Managed by `/usr/local/bin/power-manager.sh` and `/etc/cron.d/power-manager`.

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

| Bridge | Attached Physical Port | Subnet / Role |
| :--- | :--- | :--- |
| `vmbr0` | `enp12s0` (Built-in NIC) | Home LAN (`192.168.1.0/24`) |
| `vmbr1` | *None (isolated)* | Safe Zone DMZ (`10.10.10.0/24`) |
| `vmbr2` | *None (isolated)* | Malware / Unsafe Zone (`10.20.20.0/24`) |
| `vmbr3` | *None (isolated)* | Not-Sure / Testing Zone (`10.30.30.0/24`) |

---

## 🔌 Hardware Passthrough
- **Device:** Naxiang SZNX LAN 100M USB Adapter
- **Hardware ID:** `35b5:3500`
- **Assigned to:** VM 100 (OpenWrt) via `qm set 100 --usb0 host=35b5:3500` (soft non-blocking dependency).

---

## ⚡ Wake-on-LAN (WOL) Configuration

Linux network drivers frequently disable Wake-on-LAN by default (`Wake-on: d`).
To enable waking the laptop over Ethernet:

- **Interface:** `enp12s0` (MAC `b8:88:e3:e7:5e:1f`)
- **Mode:** Magic Packet (`g`)
- **Systemd Service:** `/etc/systemd/system/wol.service` (Ensures `ethtool -s enp12s0 wol g` is set on every system boot).
- **Trigger Command from Router:**
  ```bash
  ssh router "/usr/bin/etherwake -D -i br-lan b8:88:e3:e7:5e:1f"
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
