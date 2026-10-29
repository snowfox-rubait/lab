"""
Task: Out-of-Band Pi-hole DNS Sinkhole Maintenance & Local .lab Records
Targets: pihole_oob (192.168.1.135)
"""

from pyinfra.operations import files, server

# 1. Deploy Authoritative Local .lab DNS Records (/etc/pihole/custom.list)
CUSTOM_HOSTS = """# Central Homelab .lab Domain Mapping (ADR-007)
192.168.1.1 router.lab
192.168.1.2 proxmox.lab
192.168.1.130 wan.lab wan-controller.lab
192.168.1.135 pihole.lab
192.168.1.197 workstation.lab rubait.lab
192.168.1.129 vm-router.lab
10.20.20.10 ingress.lab
10.20.20.11 vaultwarden.lab
10.70.70.10 db.lab
10.70.70.11 dbbackup.lab
10.10.10.10 internal.lab
10.10.10.15 gitea.lab
10.10.10.25 n8n.lab
10.30.30.2 mqtt.lab
10.30.30.5 ha.lab
"""

server.shell(
    name="Update Pi-hole custom local DNS records",
    commands=[
        f"cat << 'EOF' > /etc/pihole/custom.list\n{CUSTOM_HOSTS}EOF",
        "pihole restartdns reload",
    ],
)

# 2. Deploy Weekly Gravity Auto-Update Cron
server.shell(
    name="Ensure weekly gravity cron update is configured",
    commands=[
        "echo '7 4 * * 7 root /usr/local/bin/pihole updateGravity >/dev/null 2>&1' > /etc/cron.d/pihole-gravity",
        "chmod 644 /etc/cron.d/pihole-gravity",
    ],
)
