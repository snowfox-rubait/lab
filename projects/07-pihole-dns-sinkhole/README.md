# 🛡️ Out-of-Band Pi-hole DNS Sinkhole & Parental Controls

> **Project ID:** `07-pihole-dns-sinkhole`  
> **Status:** Live & Production-Verified  
> **Container ID:** Proxmox LXC 205 (`pihole-oob`)  
> **Network Location:** `192.168.1.135` on `vmbr0` (Home LAN / Out-of-Band)  
> **Web Admin Interface:** `http://192.168.1.135/admin`  
> **Architectural Decision Record:** [[../../knowledge/architecture-decisions#ADR-005 Out-of-Band Pi-hole DNS Sinkhole and Strict Fallback Parental Controls|ADR-005]]

---

## 🎯 Project Objectives & Purpose

1. **Hardware Offload:** Offload all heavy DNS filtering, adblocking, and domain sinkholing away from the resource-constrained TP-Link Archer C6 v3 router (16MB flash, 128MB RAM) into the Proxmox hypervisor, preventing MT7603E wireless driver crashes and out-of-memory lockups.
2. **Universal Content Protection:** Enforce a strict network-wide baseline that eliminates adult/pornographic domains, known malware/phishing hosts, and intrusive advertising across all home devices.
3. **Fail-Safe Nightly Fallback:** Guarantee uninterrupted, filtered DNS resolution during the nightly Proxmox power-down window (00:00 to 07:00 AM) through router-enforced sequential upstream failover to Cloudflare for Families (`1.1.1.3`).
4. **Anti-Bypass Hardening:** Block unauthorized manual DNS overrides (port 53 DNAT redirection) and encrypted DNS leaks (port 853 DoT/DoQ dropping) on the physical router.

---

## 🏗️ Architecture & Component Topology

```mermaid
flowchart TD
    subgraph Home_LAN["Physical Home LAN (192.168.1.0/24)"]
        subgraph Whitelisted_Tier["Allowlisted Personal Tier"]
            PC["Main PC (192.168.1.197)"]
            Phone["User Phone (192.168.1.185)"]
            Laptop["ThinkPad Wi-Fi (192.168.1.153)"]
        end

        subgraph Restricted_Tier["Family & Guest Tier"]
            Repeater["Xiaomi Repeater V3 (192.168.1.165)"]
            ParentPhone["Parents' OPPO A31 (192.168.1.111)"]
            Guests["Guest Devices & Random MACs"]
        end

        Router["Archer C6 Physical Gateway (192.168.1.1)<br/>dnsmasq: strictorder '1'<br/>fw4: DNAT Port 53 & Drop Port 853"]
        PiHole["Pi-hole LXC 205 (192.168.1.135)<br/>StevenBlack Ad + Adult Filter (148k domains)<br/>Debian 12 | 1 vCPU | 512MB RAM"]
    end

    subgraph Upstream_Hierarchy["Router Strict Sequential DNS Upstreams"]
        Upstream1["1. 192.168.1.135 (Pi-hole OOB)<br/>Primary Sinkhole (100% queries when online)"]
        Upstream2["2. 1.1.1.3 (Cloudflare for Families)<br/>Nightly Fallback during Proxmox Sleep (00:00-07:00)"]
        Upstream3["3. 9.9.9.9 (Quad9)<br/>Malware & Phishing Protection"]
        Upstream4["4. 8.8.8.8 (Google DNS)<br/>Emergency Last Resort"]
    end

    Restricted_Tier -->|"DHCP DNS (192.168.1.1)"| Router
    Restricted_Tier -.->|"Manual DNS Override (Intercepted)"| Router
    Router -->|"1. Primary Forwarding"| Upstream1
    Upstream1 -->|"Gravity Filtering"| PiHole
    Router -->|"2. Failover when LXC 205 Offline"| Upstream2
    Upstream2 -->|"3. Fallback"| Upstream3
    Upstream3 -->|"4. Fallback"| Upstream4

    Whitelisted_Tier -->|"Direct Pi-hole Query"| PiHole
    Whitelisted_Tier -->|"Direct External Query (Bypass Permitted)"| Upstream_Hierarchy
```

---

## ⚙️ Container Specifications & Configuration

| Parameter | Value | Source / Notes |
| :--- | :--- | :--- |
| **Container ID** | `205` | Proxmox LXC |
| **Container Hostname** | `pihole-oob` | Out-of-Band Management Tier |
| **Base Image** | `debian-12-standard_12.7-1_amd64.tar.zst` | Debian 12 Bookworm |
| **Network Device** | `eth0` bridged to `vmbr0` | Home LAN / Out-of-Band Bridge |
| **Static IPv4** | `192.168.1.135/24` | Gateway: `192.168.1.1` |
| **MAC Address** | `bc:24:11:1c:d6:80` | Mapped in `.env` as `MAC_PIHOLE_OOB` |
| **Compute Quota** | 1 vCPU, 512 MB RAM, 512 MB Swap | Hypervisor isolated |
| **Disk Storage** | 4.0 GB Root Disk | `local-lvm` |
| **Hypervisor Flags** | `nesting=1`, `onboot=1` | Boots automatically with hypervisor |
| **Pi-hole Version** | Core v6.5, Web v6.6.1, FTL v6.8 | Pi-hole v6 modern architecture |

---

## 🚫 Blocklists & Filtering Boundaries

Pi-hole maintains its blocklists in SQLite database format (`/etc/pihole/gravity.db`):

### 1. Active Adlists
1. **Adlist 1 (Adware, Malware & Telemetry):**
   - **URL:** `https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts`
   - **Domains Blocked:** ~40,000+ domains.
2. **Adlist 2 (Unified Adult, Pornographic & NSFW):**
   - **URL:** `https://raw.githubusercontent.com/StevenBlack/hosts/master/alternates/porn/hosts`
   - **Unique Domains in Gravity:** **148,038 unique blocked domains**.

### 2. Multi-Tier Client Group Architecture
While the current policy enforces a uniform baseline across the entire household, clients are cleanly separated into database groups to support future granular policies without migration:
- **Group 0 (`Default`):** Contains Adlist 1 + Adlist 2. Applied to all queries forwarded by the physical router (`192.168.1.1`) and unmapped guest/repeater stations.
- **Group 1 (`Whitelisted-Devices`):** Contains Adlist 1 + Adlist 2. Assigned to personal workstation PC (`192.168.1.197`), Realme phone (`192.168.1.185`), and ThinkPad Wi-Fi (`192.168.1.153`).

---

## 🔗 Cross-Project Relationships & Interdependencies

| Related Project | Interface / Dependency Point | How It Interacts |
| :--- | :--- | :--- |
| [[../00-proxmox-host/runbook|00-proxmox-host]] | Host Hypervisor & Power Management | Hosts LXC 205 on `vmbr0`. Controls nightly sleep (00:00) and 7:00 AM RTC/WOL wake-up cycles. |
| [[../01-dual-openwrt-routing/runbook|01-dual-openwrt-routing]] | Gateway Routing, DHCP & Firewall | Upstream `dnsmasq` sequential failover, DHCP option announcement, Layer-2 `fw4` MAC allowlist, and anti-bypass DNAT rules. |
| [[../../knowledge/architecture-decisions#ADR-005 Out-of-Band Pi-hole DNS Sinkhole and Strict Fallback Parental Controls|ADR-005]] | Architectural Decision Log | Formal decision record, problem statement, threat model, and verification proofs. |
| [[../../inventory|inventory.md]] | Asset Registry | Master entry for LXC 205, `MAC_PIHOLE_OOB`, and active deployment status. |

---

## 📖 Operational Runbook Reference

For day-to-day administration, gravity updates, client-group database queries, and troubleshooting procedures, see the companion runbook:
- 📘 [[runbook|Pi-hole Operations & Maintenance Runbook]]
