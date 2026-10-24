# 🌐 Ingress vs. Egress Service Classification & Access Strategy

> **Status:** Architecture Reference Standard  
> **Key Principle:** Zero Unnecessary Public Attack Surface  
> **Remote Access Backbone:** Tailscale (Current) $\rightarrow$ Headscale Migration (Planned Post-Hardening)

---

## 🧭 Inbound vs. Outbound Classification Matrix

Not everything that uses the internet is a "public-facing online service." Confusing outbound clients with inbound listeners leads to dangerous over-exposure. Here is the strict classification of every service in the homelab:

| Service | Traffic Direction | Requires Public Ingress? | Needs Cloudflare Tunnel? | Access Mechanism |
| :--- | :--- | :---: | :---: | :--- |
| **Vaultwarden** | **Inbound (Public Ingress)** | **YES** | **YES** | `vault.snowfox.live` (Cloudflare Tunnel + BD Geo-Fence) |
| **Headscale** | **Inbound (Public Ingress)** | **YES** | **Optional / Subdomain** | `vpn.snowfox.live` (WireGuard / HTTPS Coordination) |
| **Telegram Bots (06 & 09)** | **Outbound Only (Long-Polling)**| **NO** | **NO** | Egress polling to `api.telegram.org` (No listening port) |
| **Gitea, Immich, BookStack**| **Inbound (Private LAN/Mesh)** | **NO** | **NO** | Tailscale / Safe Internal (`10.10.10.0/24`) |
| **Home Assistant Core** | **Inbound (Private LAN/Mesh)** | **NO** | **NO** | Tailscale node in `vmbr3` (`10.30.30.10`) |
| **MQTT Broker (Mosquitto)** | **Local Inbound Only** | **NO** | **NO** | Local Wi-Fi VLAN 30 (`10.30.30.2:1883`) |
| **Central Database (Postgres)**| **Isolated Offline** | **NO** | **NO** | Dedicated `vmbr7` (Internal pinholes only) |
| **Tor / Torrent (*Arr)** | **Outbound Only** | **NO** | **NO** | Outbound NAT through VPN |

---

## 🛡️ Geo-Fencing Scope: Why it Covers ALL Present & Future Public Services

In Cloudflare, the WAF rule deployed via Terraform:
```terraform
expression = "(ip.geoip.country ne \"BD\")"
action     = "block"
```
is a **Zone-Level Custom Rule** for your apex domain `snowfox.live`.

- **Universal Coverage:** Because it applies to the entire zone, it automatically protects **every single current and future subdomain** (`vault.snowfox.live`, `vpn.snowfox.live`, `git.snowfox.live`, etc.) that is proxied through Cloudflare.
- **Zero Leakage:** Any HTTP/HTTPS request originating outside Bangladesh (`country != "BD"`) is blocked at Cloudflare's Anycast edge before it can reach your tunnel or home network.

---

## 📡 Remote IoT Access via Tailscale (No Public Exposure Needed)

Your insight regarding MQTT and ESP boards is **100% correct and recommended**:
1. **IoT Isolation:** ESP32 and ESP8266 boards stay on local Wi-Fi (VLAN 30) talking plain MQTT to Mosquitto at `10.30.30.2:1883`. They never touch the public internet.
2. **Tailscale Subnet Router / Node:** By running Tailscale on the Home Assistant container or OpenWrt VM, the entire `10.30.30.0/24` subnet is accessible securely from your phone or laptop anywhere in the world.
3. **Outcome:** You get full remote control of your smart home sensors and microcontrollers with **zero open ports on the internet**.

---

## 🔄 Headscale Migration Strategy

1. **Phase 1 (Current):** Use official Tailscale coordination server. It is battle-tested, zero-maintenance, and provides instant secure mesh networking.
2. **Phase 2 (Target):** Once the core homelab (OpenWrt dual routing, Pi-hole, Central Database, and Vaultwarden) has run with 100% stability, deploy Headscale on `vmbr2` as the self-hosted control plane, switching your devices from `login.tailscale.com` to `vpn.snowfox.live`.
