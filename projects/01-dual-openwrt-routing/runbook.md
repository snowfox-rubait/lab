
## ⏱️ Router Auto-Maintenance & Scheduled Reboots

Due to known MediaTek MT7603E PCIe driver lockups after prolonged uptime, an automated 12-hour reboot schedule is enabled via cron.

- **Timezone Synchronized:** `Asia/Dhaka` (`UTC+6`).
- **Cron Service:** Enabled and started (`/etc/init.d/cron`).
- **Schedule:** `0 4,16 * * * /sbin/reboot`
  - Reboots at **4:00 AM** and **4:00 PM** local time daily.
  - Mitigates wireless driver driver hang and clears hardware buffers proactively during off-peak hours.

---

## ⏰ 7:00 AM Proxmox Laptop Auto-Wakeup
Because the ThinkPad cuts off mechanical power to internal RTC wake pins in ACPI state S5 (Poweroff), the physical router acts as the primary Wake-on-LAN wake engine:
- **Router Cron Entry:** `0 7 * * * /usr/bin/etherwake -i br-lan b8:88:e3:e7:5e:1f`
- Transmits an etherwake Magic Packet across `br-lan` at 7:00 AM every morning to boot the Proxmox server automatically.

---

## 🔀 Multi-Mode WAN Controller & Watchdog (`wan-mode`)

The router features a unified mode switcher located at `/usr/bin/wan-mode`.

### Quick Commands:
```bash
# Check current status of both WAN interfaces & active gateway:
wan-mode status

# Switch to Mode 1 (Physical Router Main):
wan-mode 1

# Switch to Mode 2 (OpenWrt VM Main - armed with 90s safety auto-revert):
wan-mode 2

# Switch to Mode 3 (Simultaneous Dual Active PPPoE over shared ONU):
wan-mode 3
```

### Safety & Auto-Rollback Behavior in Mode 2:
When `wan-mode 2` is triggered:
1. Physical router drops its PPPoE dialer and triggers OpenWrt VM's `wan_vlan`.
2. A background watchdog spawns and waits 45 seconds.
3. Tests ping connectivity to `1.1.1.1`.
4. If internet connectivity fails: Watchdog automatically re-engages Mode 1 and restores the physical WAN link! (Logs written to `/tmp/wan-mode-watchdog.log`).

---

## 🖥️ WebUI WAN Controller Dashboard (LXC 200: `nginx-home`)

A dedicated container sits on the Home bridge (`vmbr0`) running Nginx and an interactive dashboard for checking telemetry and toggling WAN modes:

- **Access URL:** **`http://192.168.1.130/`**
- **Container Specs:** Debian 12 LXC (ID 200, 1 Core, 512MB RAM, 4GB disk)
- **Features:**
  - Real-time polling of Physical Router and OpenWrt VM WAN link states.
  - Interactive Mode 1, Mode 2, and Mode 3 switching buttons with confirmation dialogues.
  - Shows raw kernel default routing table and PPPoE peer IP addresses.
  - Nginx terminates port 80 and reverse proxies into the internal control API.
