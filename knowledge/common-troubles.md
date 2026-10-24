
# ⚠️ Common Hardware, Driver & Network Troubles

> **Scope:** Known quirks, firmware crash patterns, and quick recovery triggers across homelab nodes.

---

## 📶 MediaTek Wi-Fi MCU Firmware Crash (Archer C6 v3 / MT7603E & MT7615E)

### Symptoms:
- 2.4 GHz Wi-Fi SSID disappears completely.
- 5 GHz Wi-Fi may broadcast but rejects new client associations.
- LuCI Web interface hangs indefinitely (HTTP 307 redirect loop or timeout).
- SSH works, but load average spikes to $\approx 4.0$.
- In `top` or `ps`, `hostapd` is stuck in unkillable kernel sleep state `D` (Disk/Hardware wait).
- In `dmesg`: `mt7603e 0000:01:00.0: MCU message 11 (seq 2) timed out` followed by flood of `hostapd: handle_probe_req: send failed`.

### Root Cause:
The MediaTek MT7603E wireless PCIe chip's on-die MCU microcontroller locked up. Because `hostapd` issued an ioctl to the dead radio driver, it entered an unkillable uninterruptible kernel sleep (`TASK_UNINTERRUPTIBLE` / `D`), blocking `ubus` calls. LuCI calls `ubus` to fetch wireless status, causing uHTTPd CGI requests to hang forever.

### Resolution:
Because the MCU lockup is in hardware/kernel driver state, standard `service network restart` or `wifi up` cannot unwedge the PCIe bus.
Trigger a hardware reboot from SSH:
```bash
sync && echo b > /proc/sysrq-trigger
```
Upon reboot, the PCIe reset initializes the MT7603E/MT7615E firmware cleanly, restoring both `Rubait` (2.4 GHz), `Rubait_5G`, and LuCI.

---

## 🔁 OpenWrt Scheduled Cron Reboot Loop (RTC / sysfixtime Skew)

### Symptoms:
- Router reboots continuously at the scheduled cron time (e.g., at 16:00:00).
- Ethernet link flaps down and up repeatedly every ~40–60 seconds for multiple cycles (up to 30–40 minutes).
- Proxmox kernel log reports: `enp12s0: Link is Down` followed by `Link is Up` in rapid succession.
- Syslog shows: `cron.err crond: time disparity of X minutes detected`.

### Root Cause:
1. **No Battery-Backed RTC:** Embedded consumer routers like TP-Link Archer C6 v3 do not have a real-time clock (RTC) chip.
2. **`sysfixtime` Initial Clock Guess:** During boot (`/etc/init.d/sysfixtime`), OpenWrt sets the system clock to the timestamp of the newest file found under `/etc` (e.g., `15:42`).
3. **Reboot Loop Window:** When the cron trigger `0 4,16 * * * /sbin/reboot` fired at `16:00:00`, the router rebooted (~25-35s boot time). Upon boot, before WAN/PPPoE was up and NTP could contact upstream time servers, the clock temporarily restored to `15:42` (or remained inside the `16:00` minute). Once NTP or `sysfixtime` stepped the clock, or while the clock traversed the target minute, crond matched `minute 0, hour 16` again and immediately issued another `/sbin/reboot`.
4. This cycle repeated on every boot until NTP stepped past `16:00:59` before `crond` could evaluate the rule, or until the network stabilized enough to step to `16:43`.

### Prevention & Resolution:
Never invoke bare `/sbin/reboot` in an OpenWrt cron job. Always protect scheduled reboots with an uptime threshold guard script (`/usr/bin/safe-reboot`):
```bash
#!/bin/sh
UPTIME=$(cut -d. -f1 /proc/uptime)
# Abort if router has been up for less than 10 minutes (600s)
if [ "${UPTIME:-0}" -lt 600 ]; then
    logger -t safe-reboot "Aborting scheduled reboot: system uptime is only ${UPTIME}s (< 600s)."
    exit 1
fi
logger -t safe-reboot "Scheduled reboot proceeding (uptime: ${UPTIME}s)..."
sleep 60
/sbin/reboot
```
In crontab (`/etc/crontabs/root`), use:
```crontab
0 4,16 * * * /usr/bin/safe-reboot
```
