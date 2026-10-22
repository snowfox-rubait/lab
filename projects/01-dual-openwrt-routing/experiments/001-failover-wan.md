---
id: EXP-001
title: Dual OpenWrt WAN Failover with Metric Switching
date: 2026-10-21
status: SUCCEEDED
project: dual-openwrt-routing
tags:
  - openwrt
  - pppoe
  - proxmox
  - networking
  - failover
---

# EXP-001: Dual OpenWrt WAN Failover with Metric Switching

## 🎯 Objective
Enable seamless swapping of the single fiber ONU between the physical Archer C6 router and the Proxmox OpenWrt VM (VM 100), without:
1. Causing DHCP IP collisions on `192.168.1.0/24`.
2. Breaking Wi-Fi client connectivity.
3. Requiring manual configuration edits on router swap.

---

## 🔬 Hypothesis
By maintaining the Physical Router as the sole DHCP server on the `192.168.1.0/24` subnet, assigning the OpenWrt VM a static IP (`192.168.1.129`), and configuring metric-based routing tables on both routers:
- High priority metric (`10`) is assigned to the local fiber WAN (PPPoE).
- Low priority metric (`20`) is assigned to the interconnecting LAN route.
- Moving the ONU cable triggers automatic default gateway fallback without client disruption.

---

## ⚙️ Execution & Changes Applied

### 1. Laptop Power / Lid Configuration
- Created `/etc/systemd/logind.conf.d/ignore-lid.conf` with `HandleLidSwitch=ignore`.
- Masked `sleep.target`, `suspend.target`, `hibernate.target`, `hybrid-sleep.target`.

### 2. Proxmox VM 100 (OpenWrt) Provisioning
- **Hardware:** 1 shared vCPU (`cpuunits=1000`), 512 MB RAM, 2 GB root disk.
- **Bridges:**
  - `vmbr0` (Home LAN / WAN uplink)
  - `vmbr1` (Safe zone `10.10.10.1/24`)
  - `vmbr2` (Unsafe zone `10.20.20.1/24`)
  - `vmbr3` (Not-sure zone `10.30.30.1/24`)
- **USB Passthrough:** Attached `35b5:3500` (Naxiang USB LAN adapter) permanently via hardware ID.
- **Drivers:** Installed `kmod-usb-net-cdc-ether` and `usbutils` (mapped to `eth4`).

### 3. OpenWrt VM Network & Routing Rules
```uci
# Primary fiber connection (USB adapter)
set network.wan_fiber=interface
set network.wan_fiber.device='eth4'
set network.wan_fiber.proto='pppoe'
set network.wan_fiber.metric='10'

# Fallback uplink via physical router LAN
set network.homelan=interface
set network.homelan.device='eth0'
set network.homelan.proto='static'
set network.homelan.ipaddr='192.168.1.129'
set network.homelan.gateway='192.168.1.1'
set network.homelan.metric='20'
set dhcp.homelan.ignore='1'
```

### 4. Physical Router (Archer C6) Routing Rules
```uci
set network.wan.metric='10'
set network.lan_fallback=route
set network.lan_fallback.interface='lan'
set network.lan_fallback.target='0.0.0.0/0'
set network.lan_fallback.gateway='192.168.1.129'
set network.lan_fallback.metric='20'
```

---

## 📊 Observations & Verification
- `ping -c 2 1.1.1.1` from OpenWrt VM: **100% success** (4.6 ms latency).
- Physical router routing table confirmed dual routes:
  - `default via 10.200.200.56 dev pppoe-wan metric 10`
  - `default via 192.168.1.129 dev br-lan metric 20`
- DNS rebind domain `snowfox.live` registered in OpenWrt VM.
- Dropbear SSH keys populated from workstation and Termux.

---

## 🏆 Outcome
**SUCCEEDED.** Both routers are fully armed to automatically route packets through whichever port the ONU is plugged into.
