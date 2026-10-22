# 🔧 Troubleshooting Playbook & Common Diagnostics

> **Purpose:** Quick-reference commands and diagnostic flowcharts for triage across our PC, Proxmox hypervisor, OpenWrt routers, and mobile nodes.

---

## 🔍 Fast Triage Commands

### 1. Physical Router (`ssh router`)
```bash
# Check routing table and active default route
ip route

# Check PPPoE connection state
ifstatus wan

# Check DHCP leases
cat /tmp/dhcp.leases

# Check firewall zone iptables/nftables
fw4 status
```

### 2. Proxmox Host (`ssh proxmox`)
```bash
# Check all VMs / LXCs
qm list
pct list

# Inspect hardware bridge links
ip -brief link show type bridge

# Access OpenWrt VM serial console direct socket (without GUI)
python3 -c '
import socket; s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.connect("/var/run/qemu-server/100.serial0")
s.sendall(b"ip route\n")
print(s.recv(4096).decode("utf-8", errors="replace"))
'
```

### 3. OpenWrt VM 100 (`ssh openwrt-vm` / `192.168.1.129`)
```bash
# Check if USB Ethernet adapter has carrier
ip link show eth4

# Verify WAN fiber PPPoE status
ifstatus wan_fiber

# Check upstream connectivity
ping -c 3 1.1.1.1
```

---

## 🩺 Diagnostic Playbooks

### Issue: "Internet stopped working when switching ONU cable"
1. **Check which port has carrier:**
   - On Archer C6: `ip link show wan`
   - On OpenWrt VM: `ip link show eth4`
2. **Verify active default route on Archer C6:**
   - Run `ip route`
   - If ONU is on VM, route should be: `default via 192.168.1.129 dev br-lan metric 20`
3. **Verify PPPoE negotiation on the active router:**
   - Run `logread | grep -i pppd` to see if authentication succeeded.
