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

### 4. Pi-hole DNS Sinkhole & Router Filtering (`ssh proxmox` / `ssh router`)
```bash
# Check Pi-hole service inside LXC 205:
ssh proxmox "pct exec 205 -- /usr/local/bin/pihole status"

# Check router DNS forwarding and strict sequential order:
ssh router "uci show dhcp.@dnsmasq[0].server && uci get dhcp.@dnsmasq[0].strictorder"

# Check router anti-bypass firewall rules:
ssh router "nft list chain inet fw4 dstnat_lan"
ssh router "nft list chain inet fw4 forward_lan | grep -C 2 Block-DoT-DoQ"
```

### 5. Production Services & Ingress (`ssh proxmox`)
```bash
# Wake Proxmox Host if sleeping / powered off (wait 1-2 minutes for convergence):
wake-proxmox

# Check public ingress endpoint status:
curl -I https://vault.snowfox.live/

# Inspect Cloudflare Tunnel status in LXC 202:
ssh proxmox "pct exec 202 -- systemctl status cloudflared"

# Inspect Vaultwarden container logs in LXC 220:
ssh proxmox "pct exec 220 -- docker logs --tail 25 vaultwarden"

# Inspect Central PostgreSQL status in LXC 210:
ssh proxmox "pct exec 210 -- systemctl status postgresql"
```

---

## 🩺 Diagnostic Playbooks

### Issue: "A device is accessing blocked sites or ads aren't blocked"
1. **Check if device is querying local router:**
   - Verify device is using `192.168.1.1` as DNS (or check `/tmp/dhcp.leases` on router).
2. **Check if Pi-hole LXC 205 is running:**
   - Run `ssh proxmox "pct status 205"`. If stopped, router automatically falls back to Cloudflare for Families `1.1.1.3`.
3. **Verify Pi-hole Gravity block count:**
   - Run `ssh proxmox "pct exec 205 -- sqlite3 /etc/pihole/gravity.db 'SELECT count(*) FROM gravity;'"` (should be ~148,000+ domains).
4. **Test domain directly from router:**
   - `ssh router "nslookup pornhub.com 127.0.0.1"` (Must return `0.0.0.0`).

### Issue: "Internet stopped working when switching ONU cable"
1. **Check which port has carrier:**
   - On Archer C6: `ip link show wan`
   - On OpenWrt VM: `ip link show eth4`
2. **Verify active default route on Archer C6:**
   - Run `ip route`
   - If ONU is on VM, route should be: `default via 192.168.1.129 dev br-lan metric 20`
3. **Verify PPPoE negotiation on the active router:**
   - Run `logread | grep -i pppd` to see if authentication succeeded.
