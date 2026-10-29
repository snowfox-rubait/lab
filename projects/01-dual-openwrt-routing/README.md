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
5. **Core Inter-Bridge Zero-Trust Security (ADR-006):** Segment Proxmox compute tiers across isolated virtual bridges (`vmbr1` through `vmbr7`) with default-reject forwarding, protecting the dedicated Database Zone (`vmbr7`) via strictly audited application pinholes.

---

## 📂 Project Structure & References

- 📘 **Runbook & Operations Guide:** [Routing Operations & wan-mode Runbook](runbook.md)
- 🛡️ **DNS Sinkhole & Parental Controls Subsystem:** [Project 07: Pi-hole Out-of-Band DNS Sinkhole](../07-pihole-dns-sinkhole/README.md)
- 📐 **Architectural Decision Records:**
  - [ADR-005: Out-of-Band Pi-hole & Parental Controls](../../knowledge/architecture-decisions.md#adr-005-out-of-band-pi-hole-dns-sinkhole-and-strict-fallback-parental-controls)
  - [ADR-006: Dedicated Database Tier (vmbr7) & Inter-Bridge Firewall](../../knowledge/architecture-decisions.md#adr-006-dedicated-database-tier-vmbr7-and-zero-trust-inter-bridge-firewall-hardening)
  - [ADR-002 §1.5: MAC Allowlist Architecture](../../knowledge/architecture-decisions.md#15-wi-fi-parental-controls-via-mac-allowlist)
- 🧪 **Experiments Log:**
  - [EXP-001: Dual OpenWrt WAN Failover with Metric Switching](experiments/001-failover-wan.md)
  - [EXP-002: Single-Cable VLAN Trunking & Multi-Mode Dual PPPoE](experiments/002-vlan-trunking.md)
  - [EXP-003: Single-Cable Multi-VLAN Trunking for Isolated IoT Wi-Fi (VLAN 30)](experiments/003-iot-vlan30-trunking.md)
- 🔒 **Environment Configurations:**
  - Central environment template: [Root .env.example](../../.env.example) (PPPoE credentials, DNS upstream hierarchy, hardware MAC addresses)
