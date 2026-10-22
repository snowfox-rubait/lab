# 🛡️ Per-Zone Nginx Reverse Proxy Architecture & WAN Controller

> **Project ID:** `02-per-zone-nginx-proxies`  
> **Status:** Phase 1 Completed (`nginx-home`)  
> **Architecture Principle:** Strict Network Segmentation via Isolated Reverse Proxies

---

## 🎯 1. Architectural Decision: Why One Nginx Per Zone?

In traditional homelabs, administrators often run a single central reverse proxy with network cards attached to every VLAN.
**The Vulnerability:** If that single central reverse proxy is compromised via an Nginx CVE or web application exploit, the attacker gains direct Layer-2 access to every VLAN in the entire home!

### The True Zero-Trust Model: "One Nginx Per Zone"
Instead of a single monolithic proxy, every network bridge has its own independent, isolated Nginx container:

```
[ Internet / WAN ]
       │
[ OpenWrt Firewall VM ]
       ├── (vmbr0: Home Bridge) ──────▶ [ nginx-home (LXC 200) ] ────▶ WAN WebUI Controller
       ├── (vmbr1: Safe DMZ) ─────────▶ [ nginx-safe (LXC 201) ] ────▶ Vaultwarden, n8n, Cloudflare Tunnel
       ├── (vmbr2: Malware Lab) ──────▶ [ No Ingress Proxy ]     ────▶ Completely Air-gapped
       └── (vmbr3: Untrusted Zone) ───▶ [ nginx-notsure (LXC 202) ] ─▶ Telegram Bots, Public Webhooks
```

---

## 🖥️ 2. Active Component: `nginx-home` (LXC 200)

### 2.1 Specifications
- **Container ID:** `200`
- **Hostname:** `nginx-home`
- **OS Template:** Debian 12 (Bookworm) standard amd64
- **Assigned Resources:** 1 Core, 512 MB RAM, 512 MB Swap, 4 GB Disk
- **Network Interface:** `eth0` attached to `vmbr0` (Home Bridge)
- **Static IP:** `192.168.1.130/24` (Gateway: `192.168.1.1`)
- **Web Port:** `80` (HTTP)

### 2.2 Role & Services
Hosts the **Homelab WAN Controller WebUI**:
- URL: **`http://192.168.1.130/`**
- Intercepts requests, serves modern dark-mode responsive dashboard.
- Proxies `/api/status` and `/api/set?mode=<N>` to internal Python daemon on `127.0.0.1:8080`.
- Python daemon uses automated passwordless SSH key authentication (`/root/.ssh/id_ed25519`) to execute `/usr/bin/wan-mode` on the physical router.

---

## 🐛 3. Issues Encountered & Solutions During Provisioning

1. **Issue: Proxmox LXC Systemd Nesting Warning**
   - *Symptom:* Systemd 252 threw a nesting warning upon container creation.
   - *Fix:* Executed `pct set 200 --features nesting=1` prior to container boot.
2. **Issue: SSH Command Line Escaping in Multi-line Python Scripts**
   - *Symptom:* Pushing multi-line Python code through nested `ssh ... pct exec` commands caused bash syntax errors due to string quoting.
   - *Fix:* Wrote `app.py` locally to `/tmp/app.py` and cleanly transferred it using `scp` and `pct push 200 /tmp/app.py /opt/app.py`.
3. **Issue: Dropbear SSH Key Prompt from Container**
   - *Symptom:* The container's SSH client halted waiting for interactive `(y/n)` host verification.
   - *Fix:* Configured `ssh -o StrictHostKeyChecking=no` and authorized `root@nginx-home`'s public ed25519 key inside the router's `/etc/dropbear/authorized_keys`.

---

## 📋 4. Next Implementation Milestones
- [ ] Deploy **`nginx-safe` (LXC 201)** on `vmbr1` (Safe Zone `10.10.10.10`).
- [ ] Connect `cloudflared` tunnel and Cloudflare Origin CA certificate to `nginx-safe`.
- [ ] Deploy **`nginx-notsure` (LXC 202)** on `vmbr3` (Untrusted Zone `10.30.30.10`).
