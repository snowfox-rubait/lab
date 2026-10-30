
# ⚠️ Common Hardware, Driver & Network Troubles

> **Scope:** Known quirks, firmware crash patterns, and quick recovery triggers across homelab nodes.

---

## 📶 MediaTek Wi-Fi MCU Firmware Crash (Archer C6 v3 / MT7603E & MT7615E)

### Symptoms:
- 2.4 GHz Wi-Fi SSID disappears completely.
- 5 GHz Wi-Fi may broadcast but rejects new client associations.
- LuCI Web interface hangs indefinitely (HTTP 307 redirect loop or timeout).
- SSH works, but load average spikes to $\approx 4.0$.
- In `top` or `ps`, `hostapd` is stuck in unkillable kernel sleep state `D` (Disk/Hardware wait).
- In `dmesg`: `mt7603e 0000:01:00.0: MCU message 11 (seq 2) timed out` followed by flood of `hostapd: handle_probe_req: send failed`.

### Root Cause:
The MediaTek MT7603E wireless PCIe chip's on-die MCU microcontroller locked up. Because `hostapd` issued an ioctl to the dead radio driver, it entered an unkillable uninterruptible kernel sleep (`TASK_UNINTERRUPTIBLE` / `D`), blocking `ubus` calls. LuCI calls `ubus` to fetch wireless status, causing uHTTPd CGI requests to hang forever.

### Resolution:
Because the MCU lockup is in hardware/kernel driver state, standard `service network restart` or `wifi up` cannot unwedge the PCIe bus.
Trigger a hardware reboot from SSH:
```bash
sync && echo b > /proc/sysrq-trigger
```
Upon reboot, the PCIe reset initializes the MT7603E/MT7615E firmware cleanly, restoring both `Rubait` (2.4 GHz), `Rubait_5G`, and LuCI.

---

## 🔁 OpenWrt Scheduled Cron Reboot Loop (RTC / sysfixtime Skew)

### Symptoms:
- Router reboots continuously at the scheduled cron time (e.g., at 16:00:00).
- Ethernet link flaps down and up repeatedly every ~40–60 seconds for multiple cycles (up to 30–40 minutes).
- Proxmox kernel log reports: `enp12s0: Link is Down` followed by `Link is Up` in rapid succession.
- Syslog shows: `cron.err crond: time disparity of X minutes detected`.

### Root Cause:
1. **No Battery-Backed RTC:** Embedded consumer routers like TP-Link Archer C6 v3 do not have a real-time clock (RTC) chip.
2. **`sysfixtime` Initial Clock Guess:** During boot (`/etc/init.d/sysfixtime`), OpenWrt sets the system clock to the timestamp of the newest file found under `/etc` (e.g., `15:42`).
3. **Reboot Loop Window:** When the cron trigger `0 4,16 * * * /sbin/reboot` fired at `16:00:00`, the router rebooted (~25-35s boot time). Upon boot, before WAN/PPPoE was up and NTP could contact upstream time servers, the clock temporarily restored to `15:42` (or remained inside the `16:00` minute). Once NTP or `sysfixtime` stepped the clock, or while the clock traversed the target minute, crond matched `minute 0, hour 16` again and immediately issued another `/sbin/reboot`.
4. This cycle repeated on every boot until NTP stepped past `16:00:59` before `crond` could evaluate the rule, or until the network stabilized enough to step to `16:43`.

### Prevention & Resolution:
Never invoke bare `/sbin/reboot` in an OpenWrt cron job. Always protect scheduled reboots with an uptime threshold guard script (`/usr/bin/safe-reboot`):
```bash
#!/bin/sh
UPTIME=$(cut -d. -f1 /proc/uptime)
# Abort if router has been up for less than 10 minutes (600s)
if [ "${UPTIME:-0}" -lt 600 ]; then
    logger -t safe-reboot "Aborting scheduled reboot: system uptime is only ${UPTIME}s (< 600s)."
    exit 1
fi
logger -t safe-reboot "Scheduled reboot proceeding (uptime: ${UPTIME}s)..."
sleep 60
/sbin/reboot
```
In crontab (`/etc/crontabs/root`), use:
```crontab
0 4,16 * * * /usr/bin/safe-reboot
```

---

## 🕳️ Pi-hole v6 FTL Web Server & REST API Architecture (`400 Bad Request`)

### Symptoms:
- Accessing `https://pihole.snowfox.live/` displays a broken login page or logs: `400 Bad Request: {"error":{"key":"bad_request","message":"Bad request","hint":"The API is hosted at pi.hole/api, not pi.hole/admin/api"}}`.
- Authentication calls to `/api/auth` or status probes to `/api/info/login` fail with HTTP 400.

### Root Cause:
In Pi-hole v5, the admin web UI was hosted by Lighttpd with all assets and endpoints scoped under `/admin/`. In Pi-hole v6, `pihole-FTL` embeds its own lightweight web server listening directly on port 80:
- Web UI assets reside at `/admin/` (e.g., `/admin/login`, `/admin/queries`).
- All REST API endpoints reside directly at `/api/` (e.g., `/api/info/login`, `/api/auth`).
An Nginx reverse proxy configured with `location / { proxy_pass http://192.168.1.135:80/admin/; }` rewritten `/api/*` into `/admin/api/*`, which `pihole-FTL` explicitly rejects.

### Resolution:
In [`nginx-safe.conf`](file:///home/test/Documents/Obsidian%20Vault/lab/projects/02-per-zone-nginx-proxies/nginx-safe.conf), separate the root URL redirect from path proxying:
```nginx
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name pihole.snowfox.live;

    # Exact root redirects to /admin/
    location = / {
        return 301 https://$host/admin/;
    }

    # Proxy all paths preserving original URIs (/admin/ and /api/)
    location / {
        proxy_pass http://192.168.1.135:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## ⚠️ Proxmox LXC Terraform Provider In-Place Replacement Hazard

### Symptoms:
- Running `terraform plan` or `terraform apply` on existing containers (e.g., `proxmox_virtual_environment_container.nginx_safe`) plans a destructive action: `-/+ destroy and then create replacement`.

### Root Cause:
In the `bpg/proxmox` provider (`v0.66+`), modifying or importing container attributes such as `operating_system.template_file_id`, `unprivileged`, or `user_account.keys` are marked as immutable and force full resource destruction and replacement (`forces replacement`). Running a blanket `terraform apply` will destroy production containers, wiping custom configurations and certificates.

### Prevention & Resolution:
1. Always inspect plans carefully for `-/+ destroy and then create replacement`.
2. Use resource targeting when provisioning new containers:
   ```bash
   terraform apply -target=proxmox_virtual_environment_container.short_manager
   ```
3. If an existing live container was imported and triggers replacement warnings, remove it from Terraform state until lifecycle blocks (`ignore_changes`) are properly established:
   ```bash
   terraform state rm proxmox_virtual_environment_container.nginx_safe
   ```

---

## 🔗 Short Link Manager Split Architecture & Cloudflare Worker Resolution Error

### Symptoms:
- Accessing `https://short-admin.snowfox.live/` displays an alert:
  `Failed to reach Cloudflare Worker: <urlopen error [Errno -2] Name or service not known>`.

### Architecture Clarification:
The shortener platform utilizes a dual-tier security architecture:
1. **`short-admin.snowfox.live` (Tier 2 - Private Management)**:
   - Hosted on Proxmox LXC 225 (`10.10.10.35:8080`) in the **Safe Internal Zone (`vmbr1`)**.
   - Zero inbound public access; accessed strictly via local Split-Horizon DNS / Tailscale.
   - Used by the lab administrator to generate short links and view registry tables.
2. **`short.snowfox.live` (Tier 1 - Public Redirection Edge)**:
   - Hosted globally on **Cloudflare Workers + Cloudflare KV** with a strict Bangladesh (`BD`) geo-fence.
   - Resolves publicly to Cloudflare Anycast IPs for 24/7/365 redirection (<15ms latency).

### Root Cause:
When opening the private admin UI (`short-admin.snowfox.live`), `app.py` triggers an outbound background call to `https://short.snowfox.live/api/links` to synchronize the link registry. If the Cloudflare Worker and custom domain route have not yet been deployed to Cloudflare via `wrangler`, the domain `short.snowfox.live` does not exist in DNS, triggering Python's `[Errno -2] Name or service not known`.

### Resolution:
Deploy the Cloudflare Worker and KV binding in [`projects/13-personal-url-shortener/worker/`](file:///home/test/Documents/Obsidian%20Vault/lab/projects/13-personal-url-shortener/worker/) using Wrangler (`wrangler deploy`) or Terraform. Once the worker is deployed and bound to `short.snowfox.live`, the private admin dashboard synchronizes seamlessly.

---

## ⏱️ Proxmox ThinkPad Midnight Auto-Shutdown Loop (`power-manager.sh`)

### Symptoms:
- Powering on the Proxmox ThinkPad laptop between 00:00 and 00:15 causes it to automatically shut down within 2 minutes.
- SSH sessions receive broadcast warnings: `The system will power off in 2 minutes!` and `/run/nologin` prevents new logins.

### Root Cause:
The nightly power-saving cron script (`/usr/local/bin/power-manager.sh`) executes every 2 minutes via crontab:
`*/2 * * * * /usr/local/bin/power-manager.sh`
The script checks if the local time is within the shutdown window (`CURRENT_HOUR == 0 && CURRENT_MIN <= 15`). If booted during this window, it immediately executes `shutdown -h +2`.

### Resolution:
1. If booted during the window for maintenance, immediately cancel the pending shutdown and remove the nologin lock:
   ```bash
   shutdown -c && rm -f /run/nologin
   ```
2. In `power-manager.sh`, an uptime guard ensures the machine will not trigger auto-shutdown if it has been booted for less than 15 minutes:
   ```bash
   UPTIME_MINS=$(awk '{print int($1/60)}' /proc/uptime)
   if [ "$UPTIME_MINS" -lt 15 ]; then
       logger -t power-manager "Boot grace period active (${UPTIME_MINS}m < 15m); skipping scheduled shutdown."
       exit 0
   fi
   ```

---

## 🛡️ WAN Controller (`wan.snowfox.live`) Host/Origin & NAT Allowlist

### Symptoms:
- Invoking `POST /api/set` on `https://wan.snowfox.live` returns `403 Forbidden`.

### Root Cause:
Two separate security layers rejected the request:
1. **Nginx Client IP Allowlist on LXC 200**:
   Requests originating from `vmbr1` (`10.10.10.0/24`) pass through OpenWrt VM 100 which NATs the traffic to its WAN IP `192.168.1.129`. Because `192.168.1.129` was omitted from `/etc/nginx/sites-available/wan-controller.conf`, Nginx dropped the connection with 403 Forbidden.
2. **Application Host/Origin Validation in `/opt/app.py`**:
   The backend daemon verified `ALLOWED_HOSTS = {"192.168.1.130", "127.0.0.1", "localhost", "wan.lab"}`. Requests routed via `wan.snowfox.live` passed `Host: wan.snowfox.live`, causing `app.py` to reject the request.

### Resolution:
1. Add OpenWrt VM NAT IP (`192.168.1.129`) to Nginx allowlist on LXC 200:
   `allow 192.168.1.129;`
2. Add `wan.snowfox.live` to `ALLOWED_HOSTS` in `/opt/app.py`:
   `ALLOWED_HOSTS = {"192.168.1.130", "127.0.0.1", "localhost", "wan.snowfox.live", "wan.lab"}`

---

## 📦 Cloudflare Workers KV Metadata Limit Trap (`413 Payload Too Large`)

### Symptoms:
- Creating or shortening a URL in [`projects/13-personal-url-shortener`](file:///home/test/Documents/Obsidian Vault/lab/projects/13-personal-url-shortener/README.md) fails with:
  `Failed to process request (KV PUT failed: 413 Payload Too Large)`.
- Occurs primarily when shortening URLs containing long query strings, affiliate tags, tracking parameters, or session tokens (length > ~400–500 characters).

### Root Cause:
In Cloudflare Workers KV:
- The **value** stored against a key can be up to **25 MiB**.
- The **metadata** object attached via `env.SHORT_LINKS.put(slug, destination, { metadata })` has an inviolable hard cap of **1024 bytes (1 KiB)** after JSON serialization.
When `destination` was duplicated inside `metadata` to avoid N+1 lookups during `/api/list`, any long destination URL caused `JSON.stringify(metadata)` to exceed 1024 bytes. Cloudflare Worker runtime immediately aborted the `put()` operation with HTTP 413.

### Resolution:
1. In `worker.js`, separate full storage from registry metadata previews:
   ```javascript
   const isTruncated = destination.length > 400;
   const metadata = {
     title: title ? String(title).slice(0, 100) : "",
     destination: isTruncated ? destination.slice(0, 400) : destination,
     truncated: isTruncated,
     created_at: new Date().toISOString(),
     clicks: 0
   };

   // Store full destination in the 25 MiB KV value without loss
   await env.SHORT_LINKS.put(slug, destination, { metadata });
   ```
2. In `/api/list`, lazy-load the untruncated value from KV only if `meta.truncated === true`:
   ```javascript
   let destinationUrl = meta.destination || "";
   if (meta.truncated || !destinationUrl) {
     destinationUrl = (await env.SHORT_LINKS.get(key.name)) || destinationUrl;
   }
   ```
3. Deploy updated script via Terraform in `iac/terraform/cloudflare/`.

---

## 🥷 Nginx Stealth `404 Not Found` Mapping for Protected Administrative Endpoints

### Symptoms:
- Attempting to mask a protected endpoint (like `vault.snowfox.live/admin`) by adding `error_page 403 =404;` results in Nginx returning `HTTP/1.1 302 Moved Temporarily` redirecting to the literal URI `=404`.
- Automated port scanners or directory fuzzers receive `403 Forbidden`, confirming the admin panel exists.

### Root Cause:
In Nginx configuration syntax, `error_page 403 =404;` without a URI parameter is parsed as redirecting to a location named `=404`. To return a true HTTP 404 response body without an external HTTP redirect hop, Nginx requires a named location handler.

### Resolution:
Define an internal named location `@notfound` and reference it in `error_page`:
```nginx
location @notfound {
    return 404 "404 Not Found\n";
}

location /admin {
    error_page 403 =404 @notfound;
    allow 192.168.1.197;    # Workstation PC
    allow 10.10.10.0/24;     # Internal management tier
    deny all;                # Deny all external tunnel connections (returns stealth 404)

    proxy_pass https://10.20.20.11:8443;
    ...
}
```
Unauthorized external visitors connecting via Cloudflare Tunnel receive a clean `404 Not Found` (zero information disclosure), while authorized local subnets pass through to Vaultwarden.


