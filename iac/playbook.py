"""
Master Homelab pyinfra Fleet Orchestration Playbook
Executes targeted tasks across fleet nodes based on assigned role.
"""

from pyinfra import host

# Hypervisor Host Tier
if host.data.get("role") == "hypervisor":
    from tasks import proxmox_host

# Physical Routing Tier
elif host.data.get("role") == "physical_gateway":
    from tasks import router_openwrt

# Out-of-Band Controller Tier
elif host.data.get("role") == "controller":
    from tasks import wan_controller

# Out-of-Band DNS Sinkhole Tier
elif host.data.get("role") == "dns_sinkhole":
    from tasks import pihole_oob

# Safe Internal Reverse Proxy Tier (LXC 201 on vmbr1)
elif host.data.get("role") == "safe_ingress":
    from tasks import nginx_safe

# Short Links Manager Tier (LXC 225 on vmbr1)
elif host.data.get("role") == "url_shortener_manager":
    from tasks import short_manager
