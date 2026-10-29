"""
Task: Out-of-Band WAN Controller Provisioning (LXC 200)
Targets: wan_controller (192.168.1.130)
"""

from pyinfra.operations import files, server, systemd

# 1. Deploy Python Web Controller Application
files.put(
    name="Deploy /opt/app.py",
    src="projects/01-dual-openwrt-routing/wan-controller/app.py",
    dest="/opt/app.py",
    user="root",
    group="root",
    mode="755",
)

# 2. Deploy Systemd Service Unit
files.put(
    name="Deploy /etc/systemd/system/wan-webui.service",
    src="projects/01-dual-openwrt-routing/wan-controller/wan-webui.service",
    dest="/etc/systemd/system/wan-webui.service",
    user="root",
    group="root",
    mode="644",
)

# 3. Reload Systemd and Restart WAN Controller Daemon
systemd.service(
    name="Restart and enable wan-webui.service",
    service="wan-webui",
    running=True,
    enabled=True,
    restarted=True,
)

# 4. Deploy Nginx Virtual Host Configuration
files.put(
    name="Deploy /etc/nginx/sites-available/default",
    src="projects/01-dual-openwrt-routing/wan-controller/nginx-site.conf",
    dest="/etc/nginx/sites-available/default",
    user="root",
    group="root",
    mode="644",
)

systemd.service(
    name="Reload Nginx to apply reverse proxy rules",
    service="nginx",
    running=True,
    enabled=True,
    reloaded=True,
)
