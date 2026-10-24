
# 📖 Routing Operations & wan-mode Runbook

> **Scope:** Physical Router (`192.168.1.1`), OpenWrt VM (`192.168.1.129`), VLAN 100 trunking, and WAN Mode management.

---

## ⏱️ Router Auto-Maintenance & Scheduled Reboots

Due to known MediaTek MT7603E PCIe driver lockups after prolonged uptime, an automated 12-hour reboot schedule is enabled via cron.

- **Timezone Synchronized:** `Asia/Dhaka` (`UTC+6`).
- **Cron Service:** Enabled and started (`/etc/init.d/cron`).
- **Schedule:** `0 4,16 * * * /sbin/reboot`
  - Reboots at **4:00 AM** and **4:00 PM** local time daily.
  - Mitigates wireless driver hang and clears hardware buffers proactively during off-peak hours.

---

## ⏰ 7:00 AM Proxmox Laptop Auto-Wakeup
Because the ThinkPad cuts off mechanical power to internal RTC wake pins in ACPI state S5 (Poweroff), the physical router acts as the primary Wake-on-LAN wake engine:
- **Router Cron Entry:** `0 7 * * * /usr/bin/etherwake -i br-lan <MAC_PROXMOX_BUILTIN>`
- Transmits an etherwake Magic Packet across `br-lan` at 7:00 AM every morning to boot the Proxmox server automatically.

---

## 🔀 Multi-Mode WAN Controller & Watchdog (`wan-mode`)

The router features a unified mode switcher located at `/usr/bin/wan-mode` (source tracked in repo under [[scripts/wan-mode|scripts/wan-mode]]).

### Quick Commands:
```bash
# Check current status of both WAN interfaces & active gateway:
wan-mode status

# Switch to Mode 1 (Physical Router Main):
wan-mode 1

# Switch to Mode 2 (OpenWrt VM Main - armed with 45s safety auto-revert):
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

## 🖥️ WebUI WAN Controller Dashboard (LXC 200: `wan-controller`)

A dedicated container sits on the Home bridge (`vmbr0`) running Nginx and an interactive dashboard for checking telemetry and toggling WAN modes (source files tracked in repo under [[wan-controller/app.py|wan-controller/app.py]], [[wan-controller/wan-webui.service|wan-webui.service]], and [[wan-controller/nginx-site.conf|nginx-site.conf]]):

- **Access URL:** **`http://192.168.1.130/`**
- **Container Specs:** Debian 12 LXC (ID 200, 1 Core, 512MB RAM, 4GB disk)
- **Features:**
  - Real-time polling of Physical Router and OpenWrt VM WAN link states.
  - Interactive Mode 1, Mode 2, and Mode 3 switching buttons with confirmation dialogues.
  - Shows raw kernel default routing table and PPPoE peer IP addresses.
  - Nginx terminates port 80 and reverse proxies into the internal control API.

---

## 🛡️ Wi-Fi Restrictions, Parental Controls & Anti-Bypass Firewall

> **Dedicated Project Documentation:** [[../07-pihole-dns-sinkhole/README|07-pihole-dns-sinkhole]]  
> **Architectural Decision Reference:** [[../../knowledge/architecture-decisions#ADR-005 Out-of-Band Pi-hole DNS Sinkhole and Strict Fallback Parental Controls|ADR-005]] and [[../../knowledge/architecture-decisions#15-wi-fi-parental-controls-via-mac-allowlist|ADR-002 §1.5]]

To enforce adult content blocking, ad filtering, and malware protection across the entire physical Wi-Fi network (including parents' repeaters and guest clients) without overloading the router's 16MB flash/128MB RAM:

### 1. Strict Upstream DNS Hierarchy (`dnsmasq`)
DHCP clients on the Home LAN receive **only** `192.168.1.1` as their DNS resolver. The router's `/etc/config/dhcp` forwards queries sequentially using `strictorder`:
```uci
set dhcp.@dnsmasq[0].strictorder='1'
set dhcp.@dnsmasq[0].noresolv='1'
del dhcp.@dnsmasq[0].server
add_list dhcp.@dnsmasq[0].server='192.168.1.135'  # 1. Pi-hole LXC 205 (OOB Container)
add_list dhcp.@dnsmasq[0].server='1.1.1.3'        # 2. Cloudflare for Families (Nightly Fallback: Malware + Adult Block)
add_list dhcp.@dnsmasq[0].server='9.9.9.9'        # 3. Quad9 (Malware Block)
add_list dhcp.@dnsmasq[0].server='8.8.8.8'        # 4. Google Public DNS (Emergency Last Resort)
```

**Nightly Failover Behavior:**
When Proxmox powers down at midnight (00:00 to 07:00), Pi-hole (`192.168.1.135`) goes offline. Because `strictorder` is enabled, dnsmasq seamlessly fails over to `1.1.1.3` (Cloudflare for Families). This guarantees that adult and malware blocking remains 100% active for family devices even while the server sleeps.

### 2. MAC Allowlist Configuration (`fw4` ipset)
The router maintains an nftables Layer-2 set of authorized management and personal devices in `/etc/config/firewall` (sourced from the local `.env` file):
```uci
config ipset 'mac_allowlist'
	option name 'mac_allowlist'
	option match 'src_mac'
	list entry '$MAC_MAIN_PC'            # Main Workstation PC
	list entry '$MAC_PHONE'              # User Mobile Phone
	list entry '$MAC_PROXMOX_WIFI'        # ThinkPad Wi-Fi NIC
	list entry '$MAC_PROXMOX_BUILTIN'     # Proxmox Built-in Ethernet
	list entry '$MAC_PROXMOX_LEGACY'      # Proxmox Legacy NIC
	list entry '$MAC_PIHOLE_OOB'          # Pi-hole LXC 205 (Required to prevent upstream query loop)
	list entry '$MAC_LXC_WAN_CONTROLLER'  # WAN Controller LXC 200
	list entry '$MAC_OPENWRT_VM'          # OpenWrt VM 100
```

### 3. Anti-Bypass Firewall Rules
Configured in `/etc/config/firewall` using OpenWrt 25.12 (`fw4` / nftables):

1. **DNS Interception (DNAT Port 53):**
   Catches any device attempting to bypass Pi-hole by hardcoding custom DNS (e.g., `8.8.8.8` or `1.1.1.1`):
   ```uci
   config redirect 'dns_intercept_udp'
   	option name 'Intercept-DNS-UDP'
   	option src 'lan'
   	option proto 'udp'
   	option src_dport '53'
   	option dest_port '53'
   	option target 'DNAT'
   	option ipset '!mac_allowlist'

   config redirect 'dns_intercept_tcp'
   	option name 'Intercept-DNS-TCP'
   	option src 'lan'
   	option proto 'tcp'
   	option src_dport '53'
   	option dest_port '53'
   	option target 'DNAT'
   	option ipset '!mac_allowlist'
   ```
2. **Encrypted DNS Dropping (DoT / DoQ Port 853):**
   Rejects DNS-over-TLS (Android "Private DNS") and DNS-over-QUIC for non-allowlisted devices, forcing client devices to fall back to port 53 where they are intercepted:
   ```uci
   config rule 'block_dot'
   	option name 'Block-DoT-DoQ'
   	option src 'lan'
   	option dest 'wan'
   	option proto 'tcp udp'
   	option dest_port '853'
   	option target 'REJECT'
   	option ipset '!mac_allowlist'
   ```

### 4. Operational Verification Commands
```bash
# Verify active nftables interception chain:
ssh router "nft list chain inet fw4 dstnat_lan"

# Verify active nftables DoT reject rules:
ssh router "nft list chain inet fw4 forward_lan | grep -C 2 Block-DoT-DoQ"

# Verify upstream DNS servers and strict order:
ssh router "uci show dhcp.@dnsmasq[0].server && uci get dhcp.@dnsmasq[0].strictorder"

# Test DNS filtering from the router itself:
ssh router "nslookup pornhub.com 127.0.0.1"   # Must return 0.0.0.0 (Sinkholed by Pi-hole)
ssh router "nslookup google.com 127.0.0.1"    # Must resolve successfully
```
