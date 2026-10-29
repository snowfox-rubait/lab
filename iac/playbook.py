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
