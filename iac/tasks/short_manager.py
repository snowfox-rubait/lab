"""
Task: Short Links Manager Provisioning (LXC on vmbr1)
Targets: short_manager (10.10.10.35)
"""

from pyinfra.operations import files, server, systemd

# 1. Ensure installation directory exists
files.directory(
    name="Create /opt/short-manager",
    path="/opt/short-manager",
    user="root",
    group="root",
    mode="755",
)

# 2. Deploy Python Web Controller Application
files.put(
    name="Deploy /opt/short-manager/app.py",
    src="projects/13-personal-url-shortener/manager/app.py",
    dest="/opt/short-manager/app.py",
    user="root",
    group="root",
    mode="755",
)

# 3. Deploy Systemd Service Unit
files.put(
    name="Deploy /etc/systemd/system/short-manager.service",
    src="projects/13-personal-url-shortener/manager/short-manager.service",
    dest="/etc/systemd/system/short-manager.service",
    user="root",
    group="root",
    mode="644",
)

# 4. Restart and enable daemon
systemd.service(
    name="Restart and enable short-manager.service",
    service="short-manager",
    running=True,
    enabled=True,
    restarted=True,
)
