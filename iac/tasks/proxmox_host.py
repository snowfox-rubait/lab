"""
Task: Proxmox VE Hypervisor Host Hardening & Lifecycle Management
Targets: proxmox_host (192.168.1.2)
"""

from pyinfra.operations import files, server, systemd

# 1. Deploy Fail2ban Intrusion Prevention Configuration
files.put(
    name="Deploy /etc/fail2ban/jail.local",
    src="projects/00-proxmox-host/services/jail.local",
    dest="/etc/fail2ban/jail.local",
    user="root",
    group="root",
    mode="644",
)

systemd.service(
    name="Ensure fail2ban service is active and enabled",
    service="fail2ban",
    running=True,
    enabled=True,
    restarted=True,
)

# 2. Deploy Automated Power Manager Daemon & Schedule
files.put(
    name="Deploy /usr/local/bin/power-manager.sh",
    src="projects/00-proxmox-host/scripts/power-manager.sh",
    dest="/usr/local/bin/power-manager.sh",
    user="root",
    group="root",
    mode="755",
)

files.put(
    name="Deploy power-manager cron schedule into /etc/cron.d/power-manager",
    src="projects/00-proxmox-host/services/power-manager.cron",
    dest="/etc/cron.d/power-manager",
    user="root",
    group="root",
    mode="644",
)

# 3. Kernel Samepage Merging (KSM) Configuration for RAM Optimization
server.shell(
    name="Enable KSM memory page scanning if ksmtuned is installed",
    commands=[
        "if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files | grep -q ksmtuned; then systemctl enable --now ksmtuned; fi",
    ],
)

# 4. Tailscale Subnet Router & Mesh Port Forwarding
files.put(
    name="Deploy /etc/systemd/system/tailscale-proxy-forward.service",
    src="projects/00-proxmox-host/services/tailscale-proxy-forward.service",
    dest="/etc/systemd/system/tailscale-proxy-forward.service",
    user="root",
    group="root",
    mode="644",
)

systemd.service(
    name="Ensure tailscale-proxy-forward service is active and enabled",
    service="tailscale-proxy-forward",
    running=True,
    enabled=True,
)

