# Network Traffic Filtering, Encrypted DNS & Anti-Bypass Architecture

This document details how network-level content filtering operates against modern evasion techniques including Encrypted DNS (DoH, DoT, DoQ), Encrypted Client Hello (ECH), Tor, VPN protocols, and proxy tunnels.

---

## 1. Can We Snoop SNI or Client Hello? Why Isn't That Enough?

### How SNI Inspection Historically Worked
In TLS 1.2 and standard TLS 1.3 without ECH, a client browser connecting to an HTTPS server sends an unencrypted **Client Hello** packet:
* Inside that packet is the **Server Name Indication (SNI)** field in cleartext: e.g. `server_name = "example.com"`.
* Middlebox firewalls (e.g. enterprise Palo Alto/Fortinet appliances) snoop this cleartext SNI and send a TCP Reset (`RST`) or drop packets if the domain matches a blacklist.

### Why SNI Snooping Fails with ECH
With **Encrypted Client Hello (ECH)**:
* The client splits the Client Hello into an **Outer Client Hello** (containing a generic placeholder domain, like `cloudflare.com`) and an **Inner Client Hello** (containing the real destination).
* The Inner Client Hello is **fully encrypted** using the server's public key before leaving the client device.
* The router/firewall **cannot read the real SNI** without breaking TLS encryption.

### Can We Decrypt / Inspect HTTPS? (TLS MITM Inspection)
To inspect the real SNI or HTTP payload inside an encrypted session:
* The firewall must act as a **Man-In-The-Middle (MITM) proxy**.
* It terminates TLS, decrypts the request, inspects the URL, and re-encrypts it using a locally trusted Root CA.
* **Why this is unworkable for standard residential/guest networks:**
  * Every device (family phones, guests, IoT) must manually install and trust the root certificate.
  * Mobile applications (banking, WhatsApp, Google, Apple) enforce **Certificate Pinning** and immediately refuse to connect or crash when TLS interception is attempted.

---

## 2. Does Pi-hole Block by IP Address?

**No. Pi-hole is an L7 DNS sinkhole, not a packet filter or router firewall.**
* Pi-hole only resolves hostnames to IP addresses.
* If a client connects directly to a raw IP address (e.g., `curl https://104.21.5.12/` or connecting to a VPN server IP directly), **no DNS lookup occurs**. Pi-hole is never contacted.
* **IP-level blocking must be enforced on OpenWrt / iptables / nftables**, not inside Pi-hole.

---

## 3. Why Did DoH Bypass Pi-hole on Your Network?

1. **Firewall MAC Allowlist Exemption:**
   The OpenWrt router (`192.168.1.1`) has an `ipset` named `mac_allowlist` containing your PC (`94:b8:6d:59:b8:6b`), your phone (`e2:ff:e0:37:df:5e`), and specific admin devices. Existing DNS interception rules specify:
   `ipset = '!mac_allowlist'`
   This means allowlisted devices are completely unrestricted and bypass local DNS capture.
2. **Standard Port 443 Egress:**
   DNS-over-HTTPS (DoH) uses standard **TCP port 443** (the same port as all secure web traffic). If a browser connects directly to a known DoH IP (like Cloudflare `1.1.1.1:443` or Google `8.8.8.8:443`), it bypasses Pi-hole unless those specific DoH IPs are blocked on port 443 at the router firewall.

---

## 4. How Modern Networks Neutralize Encrypted DNS & ECH

### A. Neutralizing Encrypted DNS (DoH, DoT, DoQ)
1. **Drop DoT and DoQ:**
   * Drop all outbound traffic to destination port **TCP/UDP 853** for all non-infrastructure devices.
2. **Block Known DoH Anycast Resolvers on Port 443:**
   * Block outbound TCP port 443 to well-known DoH resolver IPs (`1.1.1.1`, `1.0.0.1`, `8.8.8.8`, `8.8.4.4`, `9.9.9.9`, `149.112.112.112`, Quad9, AdGuard, NextDNS).
   * When these IPs fail to connect over HTTPS, browsers fall back to OS DNS (which gets routed to Pi-hole).
3. **Pi-hole "Canary Domain" NXDOMAIN Signaling:**
   * Pi-hole returns `NXDOMAIN` for browser canary domains (such as Firefox's `use-application-dns.net`).
   * When Firefox and Chrome receive `NXDOMAIN` on this check, they automatically disable their built-in DoH feature and revert to the network's assigned DNS server.

### B. Neutralizing ECH (Encrypted Client Hello)
* ECH cannot operate without DNS. To encrypt the Client Hello, the browser **must query for an `HTTPS` (Type 65) or `SVCB` DNS record** to retrieve the server's public key.
* If Pi-hole blocks the domain, Pi-hole returns `0.0.0.0` or `NXDOMAIN` for all record types (A, AAAA, and HTTPS).
* Without the ECH keys, the browser cannot initiate an encrypted Client Hello.
* Furthermore, blocking or dropping Type 65 (`HTTPS`) DNS queries across the board completely disables ECH across the entire network, forcing all browsers back to standard cleartext SNI.

---

## 5. Blocking Commercial VPNs, Tor & Proxies

### The Nature of Encrypted Tunnels
A VPN or Tor circuit encrypts the entire stream (DNS, SNI, IP payload) between the client and a remote server.
* **You cannot selectively filter bad domains *inside* an external encrypted tunnel.**
* To enforce filtering, the **tunnel itself must be blocked at the firewall**, forcing the client onto the bare network where Pi-hole and content filters can inspect it.

### Multi-Layer Evasion Defense:
1. **Block VPN Protocols at Router Firewall:**
   * **WireGuard:** Drop outbound UDP to ports `51820` (and restrict general outbound UDP to standard services like NTP/DNS/QUIC).
   * **OpenVPN:** Drop outbound UDP/TCP port `1194`.
   * **IPsec / IKEv2 / L2TP:** Drop outbound UDP ports `500` and `4500`, and drop IP protocols `esp` (50) and `ah` (51).
2. **Block Tor Directory Authorities & Public Relays:**
   * Maintain an `ipset` of public Tor directory authorities and guard nodes and drop outbound traffic to them.
   * If a self-hosted Tor bridge/node is run in the future, only that specific internal IP will be granted egress.
3. **Explicit Whitelisting for Proxmox Infrastructure:**
   * Allow Cloudflare Tunnel (`cloudflared`) on `nginx-public` (LXC 202) over UDP 7844 / TCP 443 to Cloudflare IPs.
   * Allow Tailscale UDP port `41641` exclusively for designated host devices.
