"""
Homelab Fleet Inventory for pyinfra Automation
Maps static IPs, canonical .lab FQDNs, and SSH parameters across physical & virtual nodes.
"""

# Physical Hypervisor Host (ThinkPad T430 / Debian 13 PVE 9.2)
proxmox_host = [
    (
        "192.168.1.2",
        {
            "ssh_user": "root",
            "ssh_key": "~/.ssh/id_rsa_gemini_codeberg",
            "hostname": "proxmox.lab",
            "role": "hypervisor",
            "os_family": "debian",
        },
    )
]

# Physical Gateway Router (TP-Link Archer C6 v3 / OpenWrt 25.12.6)
# Note: Zero remote Python dependencies; pyinfra executes POSIX /bin/sh over Dropbear
physical_router = [
    (
        "192.168.1.1",
        {
            "ssh_user": "root",
            "ssh_key": "~/.ssh/id_rsa_gemini_codeberg",
            "hostname": "router.lab",
            "role": "physical_gateway",
            "os_family": "openwrt",
        },
    )
]

# Virtual Core Router (VM 100 on Proxmox / OpenWrt 25.12.6)
openwrt_vm = [
    (
        "192.168.1.129",
        {
            "ssh_user": "root",
            "ssh_key": "~/.ssh/id_rsa_gemini_codeberg",
            "hostname": "vm-router.lab",
            "role": "virtual_router",
            "os_family": "openwrt",
        },
    )
]

# Out-of-Band WAN Controller (LXC 200 on vmbr0)
wan_controller = [
    (
        "192.168.1.130",
        {
            "ssh_user": "root",
            "ssh_key": "~/.ssh/id_rsa_gemini_codeberg",
            "hostname": "wan.lab",
            "role": "controller",
            "os_family": "debian",
        },
    )
]

# Out-of-Band Pi-hole DNS Sinkhole (LXC 205 on vmbr0)
pihole_oob = [
    (
        "192.168.1.135",
        {
            "ssh_user": "root",
            "ssh_key": "~/.ssh/id_rsa_gemini_codeberg",
            "hostname": "pihole.lab",
            "role": "dns_sinkhole",
            "os_family": "debian",
        },
    )
]

# Central Multi-Tenant Database (LXC 210 on vmbr7)
db_central = [
    (
        "10.70.70.10",
        {
            "ssh_user": "root",
            "ssh_key": "~/.ssh/id_rsa_gemini_codeberg",
            "hostname": "db.lab",
            "role": "database",
            "os_family": "debian",
        },
    )
]

# Public Reverse Proxy & Cloudflare Tunnel Ingress (LXC 202 on vmbr2)
nginx_public = [
    (
        "10.20.20.10",
        {
            "ssh_user": "root",
            "ssh_key": "~/.ssh/id_rsa_gemini_codeberg",
            "hostname": "ingress.lab",
            "role": "public_ingress",
            "os_family": "debian",
        },
    )
]

# Safe Internal Reverse Proxy & Split-Horizon TLS (LXC 201 on vmbr1)
nginx_safe = [
    (
        "10.10.10.10",
        {
            "ssh_user": "root",
            "ssh_key": "~/.ssh/id_rsa_gemini_codeberg",
            "hostname": "internal.lab",
            "role": "safe_ingress",
            "os_family": "debian",
        },
    )
]

# Production Password Manager (LXC 220 on vmbr2)
vaultwarden = [
    (
        "10.20.20.11",
        {
            "ssh_user": "root",
            "ssh_key": "~/.ssh/id_rsa_gemini_codeberg",
            "hostname": "vaultwarden.lab",
            "role": "vault",
            "os_family": "debian",
        },
    )
]

# Personal URL Shortener Admin Manager (LXC 225 on vmbr1 - Activate once LXC 225 is provisioned)
short_manager = [
    # (
    #     "10.10.10.35",
    #     {
    #         "ssh_user": "root",
    #         "ssh_key": "~/.ssh/id_rsa_gemini_codeberg",
    #         "hostname": "short.internal.lab",
    #         "role": "url_shortener_manager",
    #         "os_family": "debian",
    #     },
    # )
]
