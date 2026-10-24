---
id: EXP-002
title: Single-Cable VLAN Trunking & Multi-Mode Dual PPPoE
date: 2026-10-22
status: SUCCEEDED
project: dual-openwrt-routing
tags:
  - openwrt
  - vlan
  - pppoe
  - proxmox
  - dsa
---

# EXP-002: Single-Cable VLAN Trunking & Multi-Mode Dual PPPoE

## 🎯 Objective
Eliminate all physical cable swapping when switching between the physical Archer C6 router and the OpenWrt VM on Proxmox, and enable simultaneous dual-PPPoE dialing across a single fiber ONU over the existing Ethernet cable.

---

## 🔬 Hypothesis
By exploiting 802.1Q VLAN tagging on the Archer C6's MT7530 switch and Proxmox Linux bridges:
1. The physical WAN port can be bridged into a tagged VLAN 100 on the router's `lan3` port.
2. The single cable between router and laptop carries both untagged Home LAN (VLAN 1) and tagged raw ONU traffic (VLAN 100).
3. The Proxmox host can break out VLAN 100 (`vmbr100`) directly into the OpenWrt VM's virtual NIC (`eth5`).
4. Both routers will be in the same Layer-2 broadcast domain as the ISP's PPPoE Concentrator.

---

## ⚙️ Execution & Configuration Applied

### 1. Physical Router (`Archer C6 v3` - OpenWrt 25.12.6)
- Identified active link on port `lan3` (connected to laptop built-in NIC).
- Created VLAN 802.1Q device `lan3.100` (`vid 100` on `lan3`).
- Created virtual bridge device `br-wan` combining physical `wan` and `lan3.100`.
- Bound the router's local WAN interface to `br-wan`:
  ```uci
  set network.lan3_vlan100=device
  set network.lan3_vlan100.name='lan3.100'
  set network.lan3_vlan100.type='8021q'
  set network.lan3_vlan100.ifname='lan3'
  set network.lan3_vlan100.vid='100'

  set network.br_wan=device
  set network.br_wan.name='br-wan'
  set network.br_wan.type='bridge'
  add_list network.br_wan.ports='wan'
  add_list network.br_wan.ports='lan3.100'

  set network.wan.device='br-wan'
  commit network
  ```

### 2. Proxmox Hypervisor Host (`ThinkPad Laptop`)
- Configured `/etc/network/interfaces`:
  ```ini
  auto vmbr100
  iface vmbr100 inet manual
      bridge-ports enp12s0.100
      bridge-stp off
      bridge-fd 0
  ```
- Hot-plugged `vmbr100` to OpenWrt VM (ID 100) as `net4` (mapped as `eth5` inside the VM).

### 3. OpenWrt VM (VM 100)
- Configured standby PPPoE interface `wan_vlan` on `eth5`:
  ```uci
  set network.wan_vlan=interface
  set network.wan_vlan.device='eth5'
  set network.wan_vlan.proto='pppoe'
  set network.wan_vlan.username='$PPPOE_SECONDARY_USER'
  set network.wan_vlan.password='$PPPOE_SECONDARY_PASS'
  set network.wan_vlan.metric='10'
  set network.wan_vlan.auto='0'
  commit network
  ```

---

## 📊 Observations & Verification
- Ran `tcpdump -i eth5 -c 5 -e -nn` inside OpenWrt VM:
  - Captured live Layer-2 ISP broadcast packets and PPPoE discovery frames flowing over the single cable.
- Permanent static lease added for OpenWrt VM on physical router (`bc:24:11:d4:16:9f` ➔ `192.168.1.129`).
- Created `/usr/bin/wan-mode` script on the physical router to toggle between:
  - **Mode 1:** Physical Router Main.
  - **Mode 2:** OpenWrt VM Main (with 45s self-healing watchdog).
  - **Mode 3:** Dual Active PPPoE over shared ONU.
- Created local shortcut `~/.local/bin/wan-mode` on workstation PC for instant terminal control.

---

## 🐛 Issues Encountered & Resolution
- **Issue 1:** `bash` not found on OpenWrt during automated provisioning.
  - *Resolution:* Switched scripts to POSIX standard `/bin/sh` (BusyBox ash).
- **Issue 2:** Host verification prompt blocked automated SSH commands between router and VM.
  - *Resolution:* Added `-y` flag (Dropbear accept hostkey) and exchanged ed25519 public keys.

---

## 🏆 Outcome
**SUCCEEDED.** Full software-defined WAN switching achieved with zero physical cable movements.
