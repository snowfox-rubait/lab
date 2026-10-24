# 📖 Pi-hole Operations & Maintenance Runbook

> **Scope:** Out-of-Band Pi-hole LXC 205 (`pihole-oob`), SQLite database management, blocklist gravity updates, failover drills, and troubleshooting.

---

## 🌐 Quick Access & Endpoints

- **Web Admin Interface:** `http://192.168.1.135/admin`
- **Host Node:** ThinkPad Proxmox Hypervisor (`192.168.1.2`, `ssh proxmox`)
- **Container Execution Wrapper:**
  ```bash
  ssh proxmox "pct exec 205 -- <command>"
  ```

---

## 🛠️ Routine Operational Commands

### 1. Service Health & Status
```bash
# Check status of Pi-hole subsystems (FTL engine, port 53 listeners):
ssh proxmox "pct exec 205 -- /usr/local/bin/pihole status"

# Check LXC container uptime and memory consumption:
ssh proxmox "pct status 205"
```

### 2. Blocklist Updates & Gravity Refresh

Pi-hole automatically pulls upstream blocklists once a week on Sunday at 04:07 UTC via `/etc/cron.d/pihole` (`7 4 * * 7 pihole ... pihole updateGravity`).

For manual updates or immediate refreshes when adding new blocklists:
```bash
# Update gravity database from remote upstream blocklists:
ssh proxmox "pct exec 205 -- /usr/local/bin/pihole updateGravity"

# Reload gravity blocklists into active memory without restarting DNS:
ssh proxmox "pct exec 205 -- /usr/local/bin/pihole reloaddns"

# Restart the FTL daemon completely:
ssh proxmox "pct exec 205 -- systemctl restart pihole-FTL"
```

### 3. Password Management
```bash
# Reset or change the Web UI admin password:
ssh proxmox "pct exec 205 -- /usr/local/bin/pihole setpassword '<new_password>'"
```

---

## 🗄️ Database Management (`gravity.db`)

Pi-hole v6 manages groups, client assignments, domain lists, and adlists inside `/etc/pihole/gravity.db`.

### Common Database Inspection Queries:
```bash
# 1. View all configured groups:
ssh proxmox "pct exec 205 -- sqlite3 /etc/pihole/gravity.db 'SELECT id, name, description FROM \"group\";'"

# 2. View all adlists and their assigned groups:
ssh proxmox "pct exec 205 -- sqlite3 /etc/pihole/gravity.db '
SELECT a.id, a.address, a.comment, g.name AS group_name 
FROM adlist a 
JOIN adlist_by_group abg ON a.id = abg.adlist_id 
JOIN \"group\" g ON abg.group_id = g.id;
'"

# 3. View all client IP mappings and active group:
ssh proxmox "pct exec 205 -- sqlite3 /etc/pihole/gravity.db '
SELECT c.id, c.ip, c.comment, g.name AS group_name 
FROM client c 
JOIN client_by_group cbg ON c.id = cbg.client_id 
JOIN \"group\" g ON cbg.group_id = g.id;
'"
```

### Modifying Client Group Policies:
To assign an IP to a different group (e.g. assigning a new client `192.168.1.199` to Group 1):
```bash
ssh proxmox "pct exec 205 -- sqlite3 /etc/pihole/gravity.db \"
INSERT OR IGNORE INTO client (ip, comment) VALUES ('192.168.1.199', 'New Managed Device');
UPDATE client_by_group SET group_id = 1 WHERE client_id = (SELECT id FROM client WHERE ip = '192.168.1.199');
\" && pct exec 205 -- /usr/local/bin/pihole reloaddns"
```

---

## 🧪 Verification & End-to-End DNS Testing

Execute these tests directly from your workstation or physical router:

### 1. Test Domain Sinkholing (Ad Block & Adult Block)
```bash
# Test an ad domain directly against Pi-hole:
python3 -c "import socket; print(socket.getaddrinfo('pagead2.googlesyndication.com', 80)[0][4][0])"
# Expected output: 0.0.0.0

# Test an adult domain:
python3 -c "import socket; print(socket.getaddrinfo('pornhub.com', 80)[0][4][0])"
# Expected output: 0.0.0.0

# Test legitimate resolution:
python3 -c "import socket; print(socket.getaddrinfo('google.com', 80)[0][4][0])"
# Expected output: Valid public IPv4/IPv6
```

### 2. Nightly Failover Drill (Simulating Hypervisor Sleep)
To verify that family devices maintain filtered internet connectivity when Proxmox shuts down at midnight:
1. Temporarily stop the Pi-hole container on Proxmox:
   ```bash
   ssh proxmox "pct stop 205"
   ```
2. Run DNS queries through the physical router (`192.168.1.1`):
   ```bash
   # Router automatically forwards sequentially to Cloudflare for Families (1.1.1.3):
   ssh router "time nslookup pornhub.com 127.0.0.1"
   ```
   **Observed Benchmark Result:**
   ```
   Server:      127.0.0.1
   Address:     127.0.0.1:53
   Name:        pornhub.com
   Address:     0.0.0.0
   real:        0m 2.51s
   ```
   *(Note: The 2.5-second latency is dnsmasq waiting for the primary UDP socket timeout before querying 1.1.1.3. Once cached, subsequent queries resolve in 0.00s).*
3. Restart Pi-hole container:
   ```bash
   ssh proxmox "pct start 205"
   ```

---

## 🚨 Troubleshooting Playbook

### Issue 1: Upstream Gravity Update Fails with HTTP 404
- **Symptom:** Running `pihole updateGravity` outputs `List download failed: status code 404`.
- **Cause:** A remote blocklist URL was removed, migrated, or renamed upstream.
- **Resolution:**
  ```bash
  # Find the ID of the failing list:
  ssh proxmox "pct exec 205 -- sqlite3 /etc/pihole/gravity.db 'SELECT id, address FROM adlist;'"
  
  # Delete or update the broken adlist:
  ssh proxmox "pct exec 205 -- sqlite3 /etc/pihole/gravity.db 'DELETE FROM adlist WHERE id = <bad_id>;'"
  ssh proxmox "pct exec 205 -- /usr/local/bin/pihole updateGravity"
  ```

### Issue 2: FTL Daemon Fails to Start After Reboot
- **Symptom:** Port 53 is not listening or `pihole-FTL.service` is failed.
- **Diagnostics:**
  ```bash
  ssh proxmox "pct exec 205 -- journalctl -u pihole-FTL.service -n 50 --no-pager"
  ```
- **Common Fix:** Check if another resolver (`systemd-resolved` or `dnsmasq`) bound port 53 inside the container:
  ```bash
  ssh proxmox "pct exec 205 -- systemctl stop systemd-resolved && pct exec 205 -- systemctl disable systemd-resolved"
  ssh proxmox "pct exec 205 -- systemctl restart pihole-FTL"
  ```
