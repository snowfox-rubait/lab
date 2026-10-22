# 🛡️ Per-Zone Reverse Proxy & Out-of-Band Management Architecture

> **Project ID:** `02-per-zone-nginx-proxies`  
> **Status:** Phase 1 Completed (`wan-controller` on vmbr0)  
> **Architecture Principle:** Strict Network Segmentation via Isolated Reverse Proxies with Independent Out-of-Band Physical Management

---

## 🎯 1. Network Topology & Proxy Boundaries

To maintain strict security and high availability, our network is partitioned into two distinct management realms:
1. **Out-of-Band Physical Management (`vmbr0` / Home LAN):** Sits directly on the physical router's LAN. It does **not** rely on the OpenWrt VM. If the OpenWrt VM crashes, hangs, or is powered down, this out-of-band management interface remains 100% operational.
2. **Per-Zone Virtual Proxies (`vmbr1`, `vmbr2`, `vmbr3`):** Governed strictly by the OpenWrt Firewall VM. Each security tier runs an isolated Nginx reverse proxy so a compromised service cannot bridge across network zones.

```
                  ┌─────────────────────────────────────────────────────────┐
                  │                 Physical Router (192.168.1.1)            │
                  └────────────────────────────┬────────────────────────────┘
                                               │
                                 vmbr0 Physical LAN (192.168.1.0/24)
                        ┌──────────────────────┴──────────────────────┐
                        │                                             │
               [ Out-of-Band Controller ]                    [ OpenWrt VM (VM 100) ]
                 LXC 200 (192.168.1.130)                     WAN: 192.168.1.129
                 (Independent Fail-safe)                               │
                                            ┌─────────────────────────┼─────────────────────────┐
                                            │ (vmbr1: Safe Zone)      │ (vmbr2: Malware Lab)    │ (vmbr3: Untrusted)
                                            │ 10.10.10.0/24           │ 10.20.20.0/24           │ 10.30.30.0/24
                                            ▼                         ▼                         ▼
                                   [ nginx-safe (LXC 201) ]    [ Air-gapped / No Proxy ] [ nginx-notsure (LXC 202) ]
                                   10.10.10.10                                           10.30.30.10
                                            │                                                   │
                                   ┌────────┴────────┐                                 ┌────────┴────────┐
                               Vaultwarden, n8n, Storage                           Telegram Bots, Webhooks
```

---

## 🖥️ 2. Out-of-Band Component: `wan-controller` (LXC 200 on `vmbr0`)

### 2.1 Why LXC 200 Lives on `vmbr0`
- **Fail-safe Survival:** It directly communicates with the physical router (`192.168.1.1`). If the OpenWrt VM is completely dead or bricked during testing, you can still open `http://192.168.1.130/` from any phone or PC on the home Wi-Fi and switch WAN modes or view status.
- **Role:** Pure physical infrastructure management (WAN Mode 1/2/3 switching & physical telemetry), NOT a public application proxy.

### 2.2 Specifications
- **Container ID:** `200`
- **Hostname:** `wan-controller` (formerly `nginx-home`)
- **OS Template:** Debian 12 (Bookworm) standard amd64
- **Assigned Resources:** 1 Core, 512 MB RAM, 512 MB Swap, 4 GB Disk
- **Network Interface:** `eth0` attached to `vmbr0` (Physical LAN Bridge)
- **Static IP:** `192.168.1.130/24` (Gateway: `192.168.1.1`)
- **Web Port:** `80` (HTTP)

### 2.3 Internal Workflow
1. User accesses **`http://192.168.1.130/`**.
2. Nginx serves the responsive dashboard and proxies `/api/*` requests to an internal Python daemon on `127.0.0.1:8080`.
3. The daemon uses automated passwordless SSH key authentication (`/root/.ssh/id_ed25519`) to execute `/usr/bin/wan-mode` on the physical router (`192.168.1.1`).

---

## 🛡️ 3. Virtual Zone Proxies (Behind OpenWrt VM)

All self-hosted homelab applications live strictly behind the OpenWrt VM:

### 3.1 `nginx-safe` (LXC 201 on `vmbr1` - Safe Zone `10.10.10.0/24`)
- **Role:** Reverse proxy for private and trusted home services.
- **Target Services:**
  - Vaultwarden (Bitwarden password manager)
  - n8n (automation workflows)
  - Samba / FileBrowser / OpenMediaVault / TrueNAS (storage)
  - Immich (photo backup)
  - Headscale (Tailscale control server)
  - Pi-hole (DNS sinkhole)
  - BookStack (documentation & notes)
  - Home Assistant
- **Ingress:** Authenticated via Cloudflare Tunnel (`cloudflared`) and local OpenWrt DNS rewrite.

### 3.2 `nginx-notsure` (LXC 202 on `vmbr3` - Untrusted Zone `10.30.30.0/24`)
- **Role:** Ingress proxy for untrusted experiments and public-facing bots.
- **Target Services:**
  - Public webhooks
  - Telegram / Discord bots
  - Public Tor bridge/node monitoring
- **Firewall Rule:** OpenWrt VM drops all traffic originating from `vmbr3` into `vmbr1` (Safe) or `vmbr0` (Home LAN).

### 3.3 Malware Lab (`vmbr2` - Air-Gapped `10.20.20.0/24`)
- **Role:** Isolated detonation chamber. No reverse proxy, no inbound ingress, zero access to home LAN.

---

## 🐛 4. Provisioning Notes & Fixes Implemented

1. **Proxmox LXC Systemd Nesting:** Configured `pct set 200 --features nesting=1` to allow systemd inside Debian 12 unprivileged containers.
2. **Daemon Deployment:** Python web service cleanly transferred and managed via `systemctl enable --now wan-webui.service`.
3. **SSH Key Trust:** Authorized `root@wan-controller`'s public ed25519 key inside physical router's `/etc/dropbear/authorized_keys` with `StrictHostKeyChecking=no`.

---

## 📋 5. Next Implementation Milestones
- [ ] Deploy **`nginx-safe` (LXC 201)** on `vmbr1` (Safe Zone `10.10.10.10`).
- [ ] Connect `cloudflared` tunnel and configure private routes to `nginx-safe`.
- [ ] Deploy initial Safe Zone core services (Pi-hole, Vaultwarden, FileBrowser).
- [ ] Deploy **`nginx-notsure` (LXC 202)** on `vmbr3` (Untrusted Zone `10.30.30.10`).
