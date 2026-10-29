"""
Task: Safe Internal Reverse Proxy Provisioning (LXC 201 on vmbr1)
Targets: nginx_safe (10.10.10.10)
"""

from pyinfra.operations import files, server, systemd

# 1. Install Nginx and Certbot Cloudflare Plugin
server.packages(
    name="Install Nginx and Certbot tools",
    packages=["nginx", "certbot", "python3-certbot-dns-cloudflare"],
    present=True,
)

# 2. Deploy Nginx Configuration for *.snowfox.live
files.put(
    name="Deploy /etc/nginx/sites-available/snowfox-safe.conf",
    src="projects/02-per-zone-nginx-proxies/nginx-safe.conf",
    dest="/etc/nginx/sites-available/snowfox-safe.conf",
    user="root",
    group="root",
    mode="644",
)

# 3. Enable virtual host link
files.link(
    name="Enable snowfox-safe.conf virtual host",
    path="/etc/nginx/sites-enabled/snowfox-safe.conf",
    target="/etc/nginx/sites-available/snowfox-safe.conf",
)

# 4. Remove default site if present
files.file(
    name="Remove default site link",
    path="/etc/nginx/sites-enabled/default",
    present=False,
)

# 5. Deploy Certificate Provisioning Script
files.directory(
    name="Create /opt/scripts",
    path="/opt/scripts",
    user="root",
    group="root",
    mode="755",
)

files.put(
    name="Deploy /opt/scripts/issue-wildcard-cert.sh",
    src="projects/02-per-zone-nginx-proxies/scripts/issue-wildcard-cert.sh",
    dest="/opt/scripts/issue-wildcard-cert.sh",
    user="root",
    group="root",
    mode="755",
)

# 6. Ensure Nginx service is enabled and running
systemd.service(
    name="Ensure Nginx service is running",
    service="nginx",
    running=True,
    enabled=True,
    reloaded=True,
)
