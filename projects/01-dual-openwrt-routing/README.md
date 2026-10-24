# 🔀 Dual OpenWrt Routing Architecture & Experiment Overview

> **Project ID:** `01-dual-openwrt-routing`  
> **Status:** Live & Production-Verified  
> **Hardware Pair:** TP-Link Archer C6 v3 (Physical Gateway) + OpenWrt 25.12.6 VM 100 on Proxmox

---

## 🎯 Project Objectives

1. **High Availability WAN Routing:** Enable seamless switching between the physical router and virtual OpenWrt router without physical re-cabling.
2. **Single-Cable Trunking:** Utilize single Gigabit Ethernet trunk carrying both Home LAN traffic (`192.168.1.0/24`) and isolated WAN traffic via 802.1Q tagged VLAN 100.
3. **Automated Failsafe Switching:** Control physical WAN dialer modes (Mode 1: Physical Main, Mode 2: VM Main with 45s ping auto-rollback, Mode 3: Dual Active PPPoE).
4. **Parental Controls & Wi-Fi Restrictions (ADR-005):** Enforce network-wide ad/malware and adult domain sinkholing via strict sequential upstream DNS routing (`strictorder '1'`), Layer-2 MAC allowlisting (`fw4` nftables), DNS port 53 DNAT interception, and encrypted DNS port 853 DoT/DoQ dropping.

---

## 📂 Project Structure & References

- 📘 **Runbook & Operations Guide:** [[lab/projects/01-dual-openwrt-routing/runbook|Routing Operations & wan-mode Runbook]]
- 🛡️ **DNS Sinkhole & Parental Controls Subsystem:** [[../07-pihole-dns-sinkhole/README|Project 07: Pi-hole Out-of-Band DNS Sinkhole]]
- 📐 **Architectural Decision Record:** [[../../knowledge/architecture-decisions#ADR-005 Out-of-Band Pi-hole DNS Sinkhole and Strict Fallback Parental Controls|ADR-005]] and [[../../knowledge/architecture-decisions#15-wi-fi-parental-controls-via-mac-allowlist|ADR-002 §1.5]]
- 🧪 **Experiments Log:**
  - [[001-failover-wan|EXP-001: Dual OpenWrt WAN Failover with Metric Switching]]
  - [[002-vlan-trunking|EXP-002: Single-Cable VLAN Trunking & Multi-Mode Dual PPPoE]]
  - [[003-iot-vlan30-trunking|EXP-003: Single-Cable Multi-VLAN Trunking for Isolated IoT Wi-Fi (VLAN 30)]]
- 🔒 **Environment Configurations:**
  - Central environment template: [[../../.env.example|Root .env.example]] (PPPoE credentials, DNS upstream hierarchy, hardware MAC addresses)
