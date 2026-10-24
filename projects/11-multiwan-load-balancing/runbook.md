# 📖 Project 11: Multi-WAN (`mwan3`) Operations & Verification Runbook

> **Target Router:** TP-Link Archer C6 v3 (`192.168.1.1`)  
> **Secondary Uplink:** OpenWrt VM 100 (`192.168.1.129`)  
> **Operational Status:** Staged for Off-Peak Testing (Zero Downtime Maintained)

---

## 🛑 Pre-Flight Verification & Conditions

Before executing the live testing phase:
1. Ensure family members are **not actively using** the internet (best executed during night maintenance window or when family is away).
2. Confirm both routers are reachable on Home LAN:
   ```sh
   ping -c 2 192.168.1.1
   ping -c 2 192.168.1.129
   ```
3. Confirm Proxmox is awake and running OpenWrt VM (VM 100).

---

## 🚀 Execution Steps (Off-Peak Window)

### Phase 1: Install MWAN3 on Physical Router
```sh
ssh root@192.168.1.1 "apk update && apk add mwan3"
```
*(Package installs ~320 KB onto router overlay, leaving >5.7 MB free).*

### Phase 2: Add Secondary WAN Interface to Network & Firewall
On the physical router:
```sh
# Create logical uplink pointing to VM 100
uci set network.wan_vm=interface
uci set network.wan_vm.proto='static'
uci set network.wan_vm.device='br-lan'
uci set network.wan_vm.ipaddr='192.168.1.1'
uci set network.wan_vm.netmask='255.255.255.0'
uci set network.wan_vm.gateway='192.168.1.129'
uci set network.wan_vm.metric='20'
uci set network.wan_vm.defaultroute='0'
uci commit network

# Include wan_vm in firewall zone 'wan' for NAT masquerading
uci add_list firewall.@zone[1].network='wan_vm'
uci commit firewall

# Reload network & firewall services
/etc/init.d/network reload
/etc/init.d/firewall reload
```

### Phase 3: Copy and Enable MWAN3 Config
From workstation PC:
```sh
scp "/home/test/Documents/Obsidian Vault/lab/projects/11-multiwan-load-balancing/mwan3.config.router" root@192.168.1.1:/etc/config/mwan3
ssh root@192.168.1.1 "/etc/init.d/mwan3 enable && /etc/init.d/mwan3 start"
```

### Phase 4: Engage Mode 3 (Dual Active PPPoE)
Activate simultaneous PPPoE dialing across both routers:
```sh
ssh root@192.168.1.1 "wan-mode 3"
```

---

## 🔍 Live Diagnostics & Sanity Checks

### 1. Check Interface Health & Tracking Status
```sh
ssh root@192.168.1.1 "mwan3 status"
```
Check that both interfaces appear:
- `interface wan is online and tracking the following IP addresses:`
- `interface wan_vm is online and tracking the following IP addresses:`

### 2. Check iptables Mangle Tables & Marks
```sh
ssh root@192.168.1.1 "iptables -t mangle -vnL"
```
Verify packets are hitting `mwan3_policy_balanced_loadsharing` and receiving fwmarks.

### 3. Check Real-Time Public IP Distribution
Run from client workstation (`rubait`):
```sh
for i in {1..4}; do
    curl -s -4 --max-time 3 ifconfig.me
    echo ""
    sleep 1
done
```
In Mode 3 with load balancing active, multiple distinct ISP IP addresses will be observed across outgoing requests.

---

## 🚨 Instant Emergency Rollback (If Anything Fails)

If latency spikes, packet loss occurs, or connections drop:
```sh
ssh root@192.168.1.1 "/etc/init.d/mwan3 stop && /etc/init.d/mwan3 disable && wan-mode 1"
```
This immediately:
1. Stops the mwan3 daemon and flushes all mangle fwmarks.
2. Re-arms Mode 1 (Physical PPPoE only).
3. Restores standard internet connectivity within 3 seconds.
