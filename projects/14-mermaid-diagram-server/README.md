# 📊 Project 14: Mermaid Live Editor & Diagram Renderer (`mermaid`)

> **Node:** Proxmox VE LXC 245 (`10.10.10.26`)  
> **Hypervisor Bridge:** Safe Internal Zone (`vmbr1`, `10.10.10.0/24`)  
> **Base OS:** Debian GNU/Linux 13 (Trixie)  
> **Domain:** `https://mermaid.snowfox.live` (`mermaid.lab`)  
> **Status:** 🟢 Live & Production Verified  
> **Infrastructure as Code:** Declarative Terraform (`iac/terraform/proxmox/lxc-mermaid.tf`)

---

## 🎯 1. Overview & Architectural Role

Mermaid Live Editor is the homelab's centralized, private diagramming and architectural visualization platform. It renders flowcharts, sequence diagrams, class diagrams, state machines, entity-relationship diagrams, and Git graphs directly in the browser using simple markdown syntax.

### Key Architectural Standards:
1. **Zero Nested Container Overhead:** Rather than running Docker inside LXC (which requires kernel overlayfs and cgroups emulation), the compiled SvelteKit SPA static assets are served directly by native Nginx in Debian 13.
2. **Ultra-Low Memory Footprint:** The entire container runs with **< 15 MiB resident RAM**, leaving hypervisor CPU and memory free for database and workflow tasks.
3. **Split-Horizon DNS & Zero-Leak Ingress:** Accessible only within the internal network (`10.10.10.0/24`, LAN) or through the encrypted Tailscale mesh (`100.127.129.106`), fronted by `nginx-safe` with a valid Let's Encrypt Wildcard certificate (`*.snowfox.live`).

---

## 🏗️ 2. Network Topology & Ingress Path

```
[ LAN / Tailscale Client ]
          │
          │ HTTPS (443) -> Split-Horizon DNS (10.10.10.10)
          ▼
┌──────────────────────────────────────────────┐
│  LXC 201: nginx-safe (10.10.10.10 on vmbr1)  │
│  - Wildcard TLS (*.snowfox.live)             │
│  - Terminate TLS for mermaid.snowfox.live    │
└──────────────────────┬───────────────────────┘
                       │ HTTP (80)
                       ▼
┌──────────────────────────────────────────────┐
│  LXC 245: mermaid (10.10.10.26 on vmbr1)     │
│  - Native Nginx SPA Static Server            │
│  - /var/www/mermaid (Live Editor SvelteKit)  │
└──────────────────────────────────────────────┘
```

---

## ⚙️ 3. Resource & Provisioning Specifications

| Parameter | Value |
| :--- | :--- |
| **Container ID** | `245` |
| **Hostname** | `mermaid` (`mermaid.internal.lab`) |
| **vCPU** | 1 Core |
| **RAM** | 512 MiB (Dedicated), 512 MiB (Swap) |
| **Actual Resident RAM** | ~12–15 MiB |
| **Disk** | 4.0 GiB on `local-lvm` thin pool |
| **Bridge** | `vmbr1` (Safe Internal Zone) |
| **IP Address** | `10.10.10.26/24` (Gateway: `10.10.10.1` OpenWrt VM) |
| **DNS Resolvers** | `192.168.1.135` (Pi-hole OOB), `1.1.1.1` |
| **Reverse Proxy Target** | `http://10.10.10.26:80` |

---

## 🛠️ 4. Nginx Web Server Configuration

Inside LXC 245 (`/etc/nginx/sites-available/mermaid`):

```nginx
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    root /var/www/mermaid;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }
}
```

---

## 🔒 5. Access & Split-Horizon DNS Verification

- **Local LAN:** Pi-hole (`192.168.1.135`) and OpenWrt (`192.168.1.1` / `192.168.1.129`) map `mermaid.snowfox.live` $\rightarrow$ `10.10.10.10`.
- **Tailscale Mesh:** Android/remote devices use MagicDNS custom nameserver `100.127.129.106` for `snowfox.live`, reaching `nginx-safe` securely over wireguard encapsulation.

---

## 🔬 6. Engineering Post-Mortem: What, How, Why, Failures & Solves

### A. The "What, How, and Why" Summary
- **What:** Provisioned a dedicated, isolated Mermaid Live Editor diagramming server in Proxmox LXC 245 without running Docker inside the container.
- **How:** Extracted the compiled SvelteKit production Single Page Application (SPA) static files from `ghcr.io/mermaid-js/mermaid-live-editor:latest` into `/var/www/mermaid` in Debian 13 LXC 245, served by native Nginx on port 80, reverse-proxied via `nginx-safe` on `https://mermaid.snowfox.live`.
- **Why:** Running Docker inside LXC wastes ~200 MiB of idle RAM and requires kernel emulation. A pure static Nginx build runs on under 15 MiB resident memory with zero vulnerability surface.

### B. Failures Encountered & Engineering Solutions

#### 1. Failure: Pi-hole v6 FTL Reload Command Removed
- **Symptoms:** Adding the DNS mapping `address=/mermaid.snowfox.live/10.10.10.10` to `/etc/dnsmasq.d/05-custom-snowfox.conf` and executing `pihole-FTL reload` failed with:
  `pihole-FTL: invalid option -- 'reload'`.
- **Root Cause:** Pi-hole v6 removed the `reload` CLI parameter.
- **Engineering Solution:** Used `systemctl restart pihole-FTL` inside LXC 205, which atomically reloaded the custom dnsmasq drop-ins.

#### 2. Failure: SPA Client-Side Deep Linking Returning 404
- **Symptoms:** Direct navigation to paths like `https://mermaid.snowfox.live/edit#...` failed if Nginx searched for physical directories.
- **Root Cause:** SvelteKit uses client-side pushState routing; only `index.html` physically exists on disk.
- **Engineering Solution:** Enforced `try_files $uri $uri/ /index.html;` in `/etc/nginx/sites-available/mermaid` so all deep links fallback to the client-side router.

