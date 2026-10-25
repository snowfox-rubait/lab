# Comprehensive Anti-Bypass, VPN/Proxy Containment & Protocol Defense

This document details the multi-layer strategy to prevent network clients from bypassing DNS content filtering using Encrypted DNS (DoH, DoT, DoQ), Encrypted Client Hello (ECH), Commercial VPNs, Tor, and Proxies.

---

## 1. Why Client-Side Bypasses Occur

Standard DNS interception (DNAT port 53 to Pi-hole) only catches unencrypted DNS queries. Modern operating systems and apps attempt multiple evasion paths:

1. **DNS-over-HTTPS (DoH):** Uses standard HTTPS port 443. Queries are hidden inside encrypted HTTP POST requests to public Anycast resolvers (Cloudflare `1.1.1.1`, Google `8.8.8.8`, Quad9 `9.9.9.9`).
2. **DNS-over-TLS (DoT) & DNS-over-QUIC (DoQ):** Uses port TCP/UDP 853 to encrypt DNS directly.
3. **Encrypted Client Hello (ECH):** Encrypts the TLS SNI (Server Name Indication) using keys retrieved via DNS Type 65 (`HTTPS`) records, blinding middlebox SNI sniffers.
4. **Commercial VPN Applications:** Encapsulate all traffic (DNS, SNI, IP payload) into encrypted tunnels using WireGuard, OpenVPN, IPsec, or obfuscated HTTPS streams.
5. **Tor Network:** Connects directly to public Tor directory authorities and guard nodes via IP, ignoring local DNS completely.

---

## 2. Multi-Layer Enforcement Matrix

| Evasion Vector | Protocol / Port | Enforcement Mechanism | Responsible Node |
| :--- | :--- | :--- | :--- |
| **DoT & DoQ** | TCP / UDP 853 | Drop outbound packets to port 853 across all non-infrastructure devices. | OpenWrt Router (`fw4` nftables) |
| **DoH (Public Anycast)** | TCP 443 to DoH IPs | Drop outbound port 443 traffic destined to maintained list of public DoH resolver IP ranges. | OpenWrt Router (`fw4` nftables) |
| **DoH (Browser Canaries)**| `use-application-dns.net` | Return `NXDOMAIN` to trigger automatic browser fallback to local OS DNS. | Pi-hole (`pihole-FTL`) |
| **DoH / VPN Domains** | L7 Domain names | Subscribe to community DoH & VPN provider domain blocklists in `gravity.db`. | Pi-hole (`gravity.db`) |
| **ECH (Client Hello)** | DNS Type 65 (`HTTPS`) | Block/strip Type 65 DNS queries or return `0.0.0.0`, forcing browsers to fall back to cleartext SNI. | Pi-hole (`pihole-FTL`) |
| **WireGuard VPN** | UDP 51820 | Drop outbound UDP 51820. | OpenWrt Router (`fw4`) |
| **OpenVPN** | UDP / TCP 1194 | Drop outbound UDP and TCP 1194. | OpenWrt Router (`fw4`) |
| **IPsec / IKEv2 / L2TP** | UDP 500, 4500, IP 50/51 | Drop UDP 500, UDP 4500, protocol `esp` (50), protocol `ah` (51). | OpenWrt Router (`fw4`) |
| **Tor Network** | ~7,000 Public Guard IPs | Drop all outbound traffic to official Tor public consensus relay IP list. | OpenWrt Router (`fw4` nftables) |

---

## 3. Detailed Technical Implementations

### A. Blocking Encrypted DNS (DoT, DoQ & DoH)

#### 1. OpenWrt Firewall Rules (`fw4` / nftables):
```uci
# Block DoT and DoQ
set firewall.block_dot_doq=rule
set firewall.block_dot_doq.name='Block-DoT-DoQ-853'
set firewall.block_dot_doq.src='lan'
set firewall.block_dot_doq.dest='wan'
set firewall.block_dot_doq.proto='tcp udp'
set firewall.block_dot_doq.dest_port='853'
set firewall.block_dot_doq.target='REJECT'

# Block Known Public DoH Server IPs on Port 443
# Managed through an nftables set populated from public DoH IP blocklists
# (e.g. dibdot/DoH-IP-blocklists)
```

#### 2. Pi-hole Canary NXDOMAIN:
Modern browsers probe canary domains before enabling DoH:
* **Firefox:** `use-application-dns.net`
When Pi-hole returns `NXDOMAIN`, Firefox disables automatic DoH and uses system DNS.

### B. Neutralizing ECH (Encrypted Client Hello)
ECH cannot function without receiving the server's public key from DNS:
* A client browser queries for an **`HTTPS` (Type 65)** or `SVCB` DNS record.
* In Pi-hole / dnsmasq:
  * For blocked domains: Pi-hole returns `0.0.0.0` or `NXDOMAIN` for all record types (A, AAAA, and HTTPS), which starves the browser of encryption parameters.
  * Across the network: A dnsmasq directive `filter-rr=65` or dropping Type 65 responses instructs the browser that the server does not support ECH, compelling the browser to send standard cleartext SNI.

### C. Blocking Commercial & Mobile VPNs
Mobile VPNs use a combination of standard protocols and HTTP/HTTPS APIs:

1. **Protocol Drop Rules at Router:**
   * WireGuard: `dest_port 51820`
   * OpenVPN: `dest_port 1194`
   * IPsec / L2TP: `dest_port 500, 4500`, IP protocol `esp`
2. **Bootstrap Domain Starvation at Pi-hole:**
   Add dedicated VPN provider domain lists to Pi-hole gravity. If the client cannot resolve `api.nordvpn.com`, `auth.expressvpn.com`, or `api.surfshark.com`, the client application cannot authenticate or retrieve the current gateway IP list.
3. **Data-Center / Hosting IP Blocks:**
   Commercial VPNs run on rented VPS/hosting providers (M247, Datacamp, OVH, DigitalOcean). Loading these hosting ASN/CIDR lists into an OpenWrt firewall blocklist stops stealth protocols (Shadowsocks, V2Ray) attempting connections over port 443.

### D. Blocking Tor Traffic
* The Tor client downloads a signed consensus document containing the IP addresses of all public guard relays.
* The router periodically downloads the official Tor directory consensus from `https://check.torproject.org/torbulkexitlist` and public relay lists, loading them into an `nftables` set (`tor_relays`) and applying:
  ```nft
  iifname "br-lan" ip daddr @tor_relays drop
  ```

---

## 4. Deep Packet Inspection (DPI) & SNI Filtering: Suricata / Snort

### Why Physical Routers Struggle with DPI
* Full Deep Packet Inspection engines like **Suricata** or **Snort** reconstruct TCP streams and analyze packet payloads to read the cleartext TLS `ClientHello` SNI.
* Consumer hardware (e.g. MT7621 with 128MB RAM) lacks the memory and processing power to run Suricata with large signature rulesets without bottlenecking throughput.

### Future Proxmox Inspection Architecture & Enforcement Reality
* **Deployment Model:** DPI engines require explicit traffic visibility. An isolated container on `vmbr5` cannot see inter-bridge traffic unless traffic is routed directly through it or mirrored to it.
* **Three Supported Architectural Modes:**
  1. **Inline IPS Gateway (Active Drop):** Deploy Suricata as a routed bridge/veth gateway directly between the client zones (`vmbr1`, `vmbr3`) and the OpenWrt VM WAN egress. Suricata operates in AF_PACKET or NFQUEUE inline mode, allowing it to drop packets or inject `TCP RST` packets directly into violating streams.
  2. **Passive TAP / SPAN Sensor (Detection Only):** Proxmox port mirroring mirrors bridge traffic to a Suricata sniffing vNIC on `vmbr5`. Suricata detects signatures and logs alerts, but cannot drop packets inline. Automated response daemons parse alert logs and dispatch API blocks to OpenWrt's nftables firewall.
  3. **Router-Offloaded Proxy / Flow Accounting:** OpenWrt VM selectively redirects outbound port 80/443 traffic to an HTTP/HTTPS forward proxy for TLS inspection where CA certificates are installed on endpoints.
* **Protocol & Visibility Boundaries:**
  - Cleartext TLS `ClientHello` SNI inspection is effective only when TLS 1.3 Encrypted Client Hello (ECH) is not in use.
  - Blocking DNS HTTPS records (type 65) disrupts automatic ECH negotiation in conforming clients, but cannot prevent direct IP connections or specialized VPN tunnels.
  - Full packet payload inspection of modern end-to-end encrypted tunnels (WireGuard, OpenVPN, Tor) is limited to traffic fingerprinting, heuristics, and destination IP reputation rather than plaintext inspection.

---

## 5. Permitted Infrastructure Exceptions
All containment rules strictly exempt trusted Proxmox infrastructure:
* **Proxmox Hypervisor (`192.168.1.2`)**: Full outbound management access.
* **Public Ingress Reverse Proxy (`10.20.20.10` / LXC 202)**: Cloudflare Tunnel daemon (`cloudflared`) allowed outbound QUIC (UDP 7844) and HTTPS (TCP 443) to Cloudflare edge IPs.
* **Tailscale Nodes**: Permitted outbound UDP port 41641 and DERP relay traffic.
