# 🛡️ Proxmox VE Host Intrusion Prevention (Fail2ban)

> **Node:** Proxmox Hypervisor Host (`192.168.1.2`)  
> **Status:** 🟢 **Active & Enforced** (`systemctl status fail2ban`)  
> **Backend Engine:** `nftables-multiport` + `systemd-journald` + `pveproxy` regex polling

---

## 🎯 Architectural Role & Threat Confinement

While external internet traffic is terminated at Cloudflare's edge, internal devices on your local physical network (`192.168.1.0/24`) can reach the Proxmox host. Fail2ban protects the hypervisor against rogue local devices, compromised Wi-Fi repeaters, or LAN brute-force attacks.

### Active Protection Jails:
1. **`proxmox` Jail (Port 8006):**
   - Monitors `/var/log/pveproxy/access.log` for authentication failures.
   - **Threshold:** 3 failed login attempts within 10 minutes.
   - **Action:** 24-hour IP ban (`nftables` kernel drop).
2. **`sshd` Jail (Port 22):**
   - Monitors `systemd-journald` (`_COMM=sshd`).
   - **Threshold:** 3 failed password/key attempts within 10 minutes.
   - **Action:** 24-hour IP ban.
3. **Allowlisted Hosts (`ignoreip`):**
   - Workstation PC (`192.168.1.197`)
   - Physical Router (`192.168.1.1`)
   - Local hypervisor loopback (`127.0.0.1/8`)
   - Safe internal subnets (`10.0.0.0/8`)

---

## 📊 Dashboard & Telemetry: Does Fail2ban Have a Dashboard?

### 1. Does It Have a Native Built-in Web UI?
**No.** Fail2ban is a lightweight C/Python daemon designed to run headlessly with zero web server dependencies. It does **not** ship with a built-in web dashboard.

### 2. Available Dashboard Solutions:
- **Built-in CLI Telemetry Dashboard (`fail2ban-summary`):**  
  We deployed `/usr/local/bin/fail2ban-summary` directly on the Proxmox host. Running it instantly prints:
  - Active and historical failed attempts.
  - Active banned hosts per jail.
  - Formatted terminal overview.
- **Fail2ban Client Commands:**
  - View all jails: `fail2ban-client status`
  - View specific jail bans: `fail2ban-client status proxmox`
  - Manually unban an IP: `fail2ban-client unban <IP_ADDRESS>`
- **Optional Web Dashboards (If Desired Later):**
  - **`fail2ban-web` / `fail2web`:** A minimal Go or Python web interface exposing fail2ban stats via a clean GUI.
  - **Prometheus `prometheus-fail2ban-exporter`:** Exports metrics directly into Grafana to plot failed attempts and bans over time.
  - **Central Telegram Alerting (Project 09):** Configure Fail2ban `action_mwl` or a custom script to dispatch instant Telegram notifications when an IP is banned.
