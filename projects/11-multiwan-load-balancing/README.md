# Project 11: Multi-WAN Load Balancing (`mwan3`)

> **Status:** Stage 1 Staged & Documented (Zero Downtime / Awaiting Off-Peak Maintenance Window)  
> **Parent Architecture:** [[../01-dual-openwrt-routing/README|01-dual-openwrt-routing]] & [[../01-dual-openwrt-routing/experiments/002-vlan-trunking|EXP-002 VLAN Trunking]]  
> **Target Devices:** Physical TP-Link Archer C6 v3 (`192.168.1.1`) & Proxmox OpenWrt VM 100 (`192.168.1.129`)

---

## 🎯 Executive Summary & Objective

In **Mode 3 (Dual Active PPPoE)**, both routers simultaneously dial active PPPoE connections over the single fiber ONU via VLAN 100 trunking.
However, without Layer-4 policy routing and conntrack marking, traffic cannot dynamically distribute across both links.

This project delivers:
1. **Dynamic 50/50 Multi-WAN Load Balancing** across native fiber PPPoE (`wan`) and the OpenWrt VM PPPoE (`wan_vm`).
2. **Sticky Session Persistence** for HTTPS banking, logins, and stateful protocols (preventing abrupt IP change disconnects).
3. **Application-Aware Offloading:** Steering heavy P2P/torrent and bulk VM traffic through the high-performance OpenWrt VM, while preserving low latency for interactive traffic on the physical router.
4. **Active Link Health Monitoring:** Continuous ICMP probing (`1.1.1.1`, `8.8.8.8`, `9.9.9.9`) with sub-5-second dead link detection and transparent failover.

---

## 🏗️ Architecture & Traffic Flow

```
                      +---------------------------------------+
                      |               Fiber ONU               |
                      +---------------------------------------+
                                          |
                        +-----------------+-----------------+
                        | Tagged VLAN 100 | Tagged VLAN 100 |
                        v                 v
            +-----------------------+   +-----------------------+
            |  Archer C6 (Physical) |   |    OpenWrt VM 100     |
            |     PPPoE (wan)       |   |   PPPoE (wan_vlan)    |
            |   Metric 10 / IP_A    |   |   Metric 10 / IP_B    |
            +-----------------------+   +-----------------------+
                        |                           |
                        |      192.168.1.0/24       |
                        +<==== Inter-Router =======>+
                        |      (Home Bridge)        |
                        v                           v
              [mwan3 Policy Engine]         [Zone Bridges]
              - Sticky HTTPS (443)          - vmbr1 (Safe 10.10.10.x)
              - Balanced HTTP/UDP           - vmbr2 (Public 10.20.20.x)
              - P2P Offload to VM           - vmbr3 (IoT 10.30.30.x)
```

---

## 📦 Package Requirements & Footprint Audit

- **Package:** `mwan3` (v2.12.0-r3)
- **Engine:** `iptables-nft` / `kmod-nft-compat` conntrack marking.
- **Flash Storage Budget on Archer C6:**
  - Flash free space before install: **6,140 KB (8% used)**.
  - Package download size: **~84 KB**.
  - Total dependencies (`ip-tiny`, `ipset`, `libxtables12`, `kmod-nft-compat`, etc.): **~320 KB**.
  - Remaining flash after installation: **~5.7 MB** (Leaves ample safety buffer > 85%).

---

## 🛠️ Step-by-Step Staged Deployment Plan (Off-Peak Window)

> [!IMPORTANT]
> **Zero Downtime Protocol:**
> Do NOT execute these steps while family members or active services are relying on internet access. Run these during designated off-peak hours (e.g. night maintenance window).

### Step 1: Update Repositories & Install `mwan3`
On the Physical Router (`192.168.1.1`):
```sh
ssh root@192.168.1.1
apk update
apk add mwan3
```

### Step 2: Define Secondary WAN Gateway in Network Config
Append the logical `wan_vm` interface pointing to the OpenWrt VM in `/etc/config/network`:
```uci
uci set network.wan_vm=interface
uci set network.wan_vm.proto='static'
uci set network.wan_vm.device='br-lan'
uci set network.wan_vm.ipaddr='192.168.1.254'
uci set network.wan_vm.netmask='255.255.255.0'
uci set network.wan_vm.gateway='192.168.1.129'
uci set network.wan_vm.metric='20'
uci set network.wan_vm.defaultroute='0'
uci commit network
/etc/init.d/network reload
```
> [!NOTE]
> **Transit Network Topology:**
> `wan_vm` binds to `br-lan` using dedicated secondary transit address `192.168.1.254/24` (preventing collision with local router IP `192.168.1.1`). Outbound packets steered to `wan_vm` are routed across the inter-router link to VM gateway `192.168.1.129`, where they traverse the VM's NAT and exit via `wan_vlan`. Dedicated policy tables in `mwan3` mark traffic by fwmark, avoiding routing loops or LAN bridge ambiguities.

### Step 3: Register `wan_vm` in Firewall WAN Zone
In `/etc/config/firewall`, add `wan_vm` to zone `wan` so masquerade NAT applies to routed outbound packets:
```uci
uci add_list firewall.@zone[1].network='wan_vm'
uci commit firewall
/etc/init.d/firewall reload
```

### Step 4: Apply Multi-WAN Routing Policies
Deploy the tested configuration file located at `projects/11-multiwan-load-balancing/mwan3.config.router` to `/etc/config/mwan3`:
```sh
scp "projects/11-multiwan-load-balancing/mwan3.config.router" root@192.168.1.1:/etc/config/mwan3
ssh root@192.168.1.1 "/etc/init.d/mwan3 restart && /etc/init.d/mwan3 enable"
```

---

## 🧪 Verification & Health Check Commands

After deployment, run the following verification checks:

1. **MWAN3 Status Overview:**
   ```sh
   ssh root@192.168.1.1 "mwan3 status"
   ```
   *Expected:* Both `wan` and `wan_vm` show status `online`, with active tracking pings.

2. **Verify Multi-WAN Marking Rules:**
   ```sh
   ssh root@192.168.1.1 "mwan3 rules"
   ```

3. **Live Public IP Split Test (from PC or VM):**
   ```sh
   # Test request 1:
   curl -4 icanhazip.com
   # Test request 2 (with alternate port or new session):
   curl -4 ifconfig.me
   ```

---

## 🔄 Emergency Rollback Procedure

If any connection anomaly or packet loss occurs during testing:
```sh
ssh root@192.168.1.1
/etc/init.d/mwan3 stop
/etc/init.d/mwan3 disable
wan-mode 1
```
*Result:* Immediately reverts to standard single-WAN Mode 1 routing with 0% lingering packet marking.
