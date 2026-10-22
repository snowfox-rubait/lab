
## 📶 MediaTek Wi-Fi MCU Firmware Crash (Archer C6 v3 / MT7603E)

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
