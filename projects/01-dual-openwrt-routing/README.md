# 🔀 Dual OpenWrt Routing Architecture & Experiment Overview

> **Project ID:** `01-dual-openwrt-routing`  
> **Status:** Live & Production-Verified  
> **Hardware Pair:** TP-Link Archer C6 v3 (Physical Gateway) + OpenWrt 25.12.6 VM 100 on Proxmox

---

## 🎯 Project Objectives

1. **High Availability WAN Routing:** Enable seamless switching between the physical router and virtual OpenWrt router without physical re-cabling.
2. **Single-Cable Trunking:** Utilize single Gigabit Ethernet trunk carrying both Home LAN traffic (`192.168.1.0/24`) and isolated WAN traffic via 802.1Q tagged VLAN 100.
3. **Automated Failsafe Switching:** Control physical WAN dialer modes (Mode 1: Physical Main, Mode 2: VM Main with 45s ping auto-rollback, Mode 3: Dual Active PPPoE).

---

## 📂 Project Structure & References

- 📘 **Runbook & Operations Guide:** [[lab/projects/01-dual-openwrt-routing/runbook|Routing Operations & wan-mode Runbook]]
- 🧪 **Experiments Log:**
  - [[001-failover-wan|EXP-001: Dual OpenWrt WAN Failover with Metric Switching]]
  - [[002-vlan-trunking|EXP-002: Single-Cable VLAN Trunking & Multi-Mode Dual PPPoE]]
- 🔒 **Environment Configurations:**
  - Configuration template: `.env.example` (PPPoE credentials, static gateway mappings)
