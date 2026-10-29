"""
Task: Physical Gateway OpenWrt Provisioning & Routing Safeguards
Targets: physical_router (192.168.1.1)
Platform: OpenWrt 25.12.6 (POSIX ash / Dropbear)
"""

from pyinfra.operations import files, server

# 1. Deploy WAN Mode Switcher Script with Three-Way Verification Watchdog
files.put(
    name="Deploy /usr/bin/wan-mode",
    src="projects/01-dual-openwrt-routing/scripts/wan-mode",
    dest="/usr/bin/wan-mode",
    user="root",
    group="root",
    mode="755",
)

# 2. Ensure Golden Mode 1 Network Backup Exists
server.shell(
    name="Preserve golden known-good Mode 1 configuration",
    commands=[
        "[ -f /etc/config/network.mode1.gold ] || cp /etc/config/network /etc/config/network.mode1.gold",
    ],
)

# 3. Ensure Sequential DNS Upstream & Strictorder in dnsmasq
server.shell(
    name="Enforce strictorder and local DNS upstream hierarchy in dnsmasq",
    commands=[
        "uci set dhcp.@dnsmasq[0].strictorder='1'",
        "uci set dhcp.@dnsmasq[0].local='/lab/'",
        "uci set dhcp.@dnsmasq[0].domain='lab'",
        "uci commit dhcp",
        "/etc/init.d/dnsmasq reload",
    ],
)
