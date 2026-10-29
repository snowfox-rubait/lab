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
| **Personal URL Shortener (13)** | **Public Edge / Private Admin**| **YES (Edge)** / **NO (Admin)**| **NO** | Public: `short.snowfox.live` (Cloudflare Worker + BD Geo-Fence)<br>Admin: `short-admin.snowfox.live` (`10.10.10.35` on `vmbr1`) |
| **Internal Web Portals (PVE, OpenWrt, Pi-hole, WAN)** | **Internal LAN / Mesh Inbound** | **NO** | **NO** | `*.snowfox.live` via `nginx-safe` (`10.10.10.10` on `vmbr1`) + Split DNS |
| **Headscale** | **Undecided / Future Evaluation** | **Deferred** | **Deferred** | Separated from `vmbr2`; deferred until core stack is battle-tested |
| **Telegram Bots (06 & 09)** | **Outbound Only (Long-Polling)**| **NO** | **NO** | Egress polling to `api.telegram.org` (No listening port) |
| **Gitea, Immich, BookStack**| **Inbound (Private LAN/Mesh)** | **NO** | **NO** | Tailscale / Split DNS (`*.snowfox.live`) / Safe Internal (`10.10.10.0/24`) |
| **Home Assistant Core** | **Inbound (Private LAN/Mesh)** | **NO** | **NO** | Tailscale node in `vmbr3` (`10.30.30.10`) |
| **MQTT Broker (Mosquitto)** | **Local Inbound Only** | **NO** | **NO** | Local Wi-Fi VLAN 30 (`10.30.30.2:1883`) |
| **Central Database (Postgres)**| **Isolated Offline** | **NO** | **NO** | Dedicated `vmbr7` (Internal pinholes only) |
| **Torrent (*Arr Stack)** | **Outbound Only** | **NO** | **NO** | Outbound NAT through VPN |

---

## 🛡️ Geo-Fencing Scope: Why it Covers ALL Present & Future Public Services

In Cloudflare, the WAF rule deployed via Terraform:
```terraform
expression = "(ip.geoip.country ne \"BD\" and http.host ne \"simplearch.snowfox.live\")"
action     = "block"
```
is a **Zone-Level Custom Rule** for your apex domain `snowfox.live`.

- **Universal Coverage with Scoped Exceptions:** Protects private internal subdomains (`vault.snowfox.live`, `vpn.snowfox.live`, etc.) by restricting ingress strictly to Bangladesh (`country == "BD"`), while explicitly exempting global public community tools like `simplearch.snowfox.live`.
- **Zero Leakage:** Any non-BD traffic targeting protected subdomains is dropped at Cloudflare's Anycast edge before reaching the tunnel or homelab.

---

## 📡 Remote IoT Access via Tailscale (No Public Exposure Needed)

Your insight regarding MQTT and ESP boards is **100% correct and recommended**:
1. **IoT Isolation:** ESP32 and ESP8266 boards stay on local Wi-Fi (VLAN 30) talking plain MQTT to Mosquitto at `10.30.30.2:1883`. They never touch the public internet.
2. **Tailscale Subnet Router / Node:** By running Tailscale on the Home Assistant container or OpenWrt VM, the entire `10.30.30.0/24` subnet is accessible securely from your phone or laptop anywhere in the world.
3. **Outcome:** You get full remote control of your smart home sensors and microcontrollers with **zero open ports on the internet**.

---

## 🔄 Headscale Migration Status (Deferred & Separated)

- **Separated from Public Bridge (`vmbr2`):** Headscale has been completely decoupled and removed from the active Public Ingress bridge (`vmbr2`) scope. Vaultwarden is currently the **sole** active service in the public ingress tier.
- **Undecided Architecture:** Future hosting placement (whether an independent bridge, an isolated DMZ, or hosted separately) is marked as **Undecided**.
- **Current Strategy:** Continue using official Tailscale for remote access. Headscale evaluation is completely out of current scope and deferred until the entire primary homelab fleet is battle-tested and mature.
