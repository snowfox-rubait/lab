# 🌐 Split-Horizon DNS & Wildcard HTTPS Engineering Guide

> **Authoritative ADR:** [ADR-008 (Split-Horizon DNS & Wildcard HTTPS)](../../knowledge/architecture-decisions.md#adr-008-split-horizon-dns-with-wildcard-lets-encrypt-via-dns-01-for-zero-leak-internal-https)  
> **Target Domain:** `*.snowfox.live`  
> **Reverse Proxy Node:** `nginx-safe` (LXC 201 on `10.10.10.10` in `vmbr1`)  
> **Primary Resolver:** OpenWrt `dnsmasq` (`192.168.1.1` / `192.168.1.129`) & Pi-hole OOB (`192.168.1.135`)  
> **Security Model:** **Zero Public Ingress** + **Zero Topology Leakage** + **100% Valid Public CA TLS**

---

## 🎯 1. Overview & Operational Problem

### The Problem
When hosting internal homelab portals (Proxmox, Gitea, n8n, Pi-hole, LuCI), standard setups suffer from two major friction points:
1. **Self-Signed Certificates / Browser Warnings:** Accessing services via raw IP/port (`https://192.168.1.2:8006` or `https://10.10.10.15:3000`) triggers disturbing red browser warnings and blocks WebSockets / PWAs.
2. **Public Exposure Risk:** If you create public DNS A-records pointing to local IPs or open router ports to validate HTTP Let's Encrypt certificates, public scanners enumerate your network topology, and router anti-DNS-rebinding filters drop your queries.

### The Solution: Split-Horizon DNS + DNS-01 Wildcard
- **Private Subdomain Resolution:** Only your home network resolvers answer queries for internal subdomains (`gitea.snowfox.live`, `pve.snowfox.live`) pointing to `10.10.10.10`.
- **Public Cloudflare DNS is Blank:** Outside visitors receive `NXDOMAIN`. Zero IPs or service names are leaked.
- **Valid Let's Encrypt Wildcard (`*.snowfox.live`):** Generated via Cloudflare API DNS TXT records (`dns-01`). **Zero public inbound ports are ever opened**.
- **Clean Standard Port 443:** Nginx handles TLS termination and proxies to backend services without requiring port numbers in the URL.

```
═════════════════════════════════════════════════════════════════════════════════
                  INTERNAL CLIENT (LAN / TAILSCALE / WI-FI)
═════════════════════════════════════════════════════════════════════════════════
                                     │
                  Requests: https://gitea.snowfox.live
                                     │
                                     ▼
                     Local OpenWrt / Pi-hole DNS
                     (Authoritative Split-Horizon)
                     - address=/gitea.snowfox.live/10.10.10.10
                     - rebind_domain=snowfox.live
                                     │
                                     ▼
                ┌─────────────────────────────────────────┐
                │        nginx-safe (LXC 201)             │
                │        IP: 10.10.10.10 (vmbr1)          │
                │  TLS: *.snowfox.live (Let's Encrypt)    │
                │  Port: 443 HTTPS (Standard / Trusted)   │
                └────────────────────┬────────────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         │                           │                           │
         ▼                           ▼                           ▼
[ Gitea (10.10.10.15:3000) ]  [ n8n (10.10.10.25:5678) ]  [ Proxmox (192.168.1.2:8006) ]

═════════════════════════════════════════════════════════════════════════════════
                     PUBLIC INTERNET / EXTERNAL SCANNERS
═════════════════════════════════════════════════════════════════════════════════
                                     │
                  Resolves https://gitea.snowfox.live
                                     ▼
                        Cloudflare Public DNS
                                     ▼
                       NXDOMAIN (Zero IP Leakage)
```

---

## 📋 2. Step-by-Step Implementation Runbook

### Step 1: Create Cloudflare API Token for DNS-01 Challenge
1. Log into your [Cloudflare Dashboard](https://dash.cloudflare.com/profile/api-tokens).
2. Go to **My Profile** $\rightarrow$ **API Tokens** $\rightarrow$ **Create Token**.
3. Select the template **Edit zone DNS** (or custom token):
   - **Token name:** `homelab-wildcard-cert-dns01`
   - **Permissions:** `Zone` $\rightarrow$ `DNS` $\rightarrow$ `Edit`
   - **Zone Resources:** `Include` $\rightarrow$ `Specific zone` $\rightarrow$ `snowfox.live`
4. Click **Continue to summary** $\rightarrow$ **Create Token**.
5. Save the generated token securely in your password manager.

---

### Step 2: Deploy Container `nginx-safe` on `vmbr1`
On your Proxmox host (`192.168.1.2`):
```bash
# Create Debian 13 LXC 201 attached to vmbr1 (Safe Internal)
pct create 201 local:vztmpl/debian-13-standard_13.6-1_amd64.tar.zst \
  --hostname nginx-safe \
  --cores 1 \
  --memory 512 \
  --swap 512 \
  --net0 name=eth0,bridge=vmbr1,ip=10.10.10.10/24,gw=10.10.10.1 \
  --nameserver "192.168.1.135 1.1.1.1" \
  --features nesting=1 \
  --unprivileged 1 \
  --onboot 1 \
  --rootfs local-lvm:4 \
  --ssh-public-keys /root/.ssh/authorized_keys \
  --start 1
```

---

### Step 2.1: Inter-Bridge Routing & Firewall Interconnection
To allow clients on Home LAN (`192.168.1.0/24`) to route to `10.10.10.10` with sub-2ms latency:

1. **On Physical Router (`192.168.1.1`):**
   - Add kernel static route for Proxmox zones via OpenWrt VM (`192.168.1.129`):
     ```bash
     uci set network.route_proxmox_zones=route
     uci set network.route_proxmox_zones.interface='lan'
     uci set network.route_proxmox_zones.target='10.0.0.0/8'
     uci set network.route_proxmox_zones.gateway='192.168.1.129'
     uci commit network && /etc/init.d/network reload
     ```
   - Advertise RFC 3442 Classless Static Routes via DHCP options 121 and 249 so all LAN/Wi-Fi clients learn the route:
     ```bash
     uci add_list dhcp.lan.dhcp_option='121,10.0.0.0/8,192.168.1.129'
     uci add_list dhcp.lan.dhcp_option='249,10.0.0.0/8,192.168.1.129'
     uci commit dhcp && /etc/init.d/dnsmasq reload
     ```
   - Add persistent firewall4 srcnat masquerade rule in `/etc/nftables.d/20-proxmox-zones-masq.nft` to prevent asymmetric TCP state drops for Wi-Fi stations:
     ```bash
     cat <<'EOF' > /etc/nftables.d/20-proxmox-zones-masq.nft
     chain srcnat_proxmox {
         type nat hook postrouting priority 100; policy accept;
         ip daddr 10.0.0.0/8 oifname "br-lan" masquerade
     }
     EOF
     fw4 reload
     ```

2. **On OpenWrt Core Router VM (`192.168.1.129`):**
   - Permit bidirectional forwarding between `lan` (Home LAN) and `safe_internal` (`vmbr1`):
     ```bash
     uci set firewall.fwd_safe_lan=forwarding
     uci set firewall.fwd_safe_lan.src='safe_internal'
     uci set firewall.fwd_safe_lan.dest='lan'
     uci add firewall forwarding
     uci set firewall.@forwarding[-1].src='lan'
     uci set firewall.@forwarding[-1].dest='safe_internal'
     uci commit firewall && /etc/init.d/firewall reload
     ```

---

### Step 3: Issue Wildcard Certificate via DNS-01 Challenge
Inside LXC 201 (`10.10.10.10`):
1. Install prerequisites:
   ```bash
   apt update && apt install -y certbot python3-certbot-dns-cloudflare nginx
   ```
2. Store your Cloudflare credentials securely:
   ```bash
   mkdir -p /etc/letsencrypt
   cat <<'EOF' > /etc/letsencrypt/cloudflare.ini
   dns_cloudflare_api_token = YOUR_CLOUDFLARE_API_TOKEN_HERE
   EOF
   chmod 600 /etc/letsencrypt/cloudflare.ini
   ```
3. Run the automated certificate acquisition script:
   ```bash
   # Using the lab repository script:
   /opt/scripts/issue-wildcard-cert.sh
   ```
   *Result:* Certbot creates temporary `_acme-challenge.snowfox.live` TXT records on Cloudflare via API, Let's Encrypt verifies domain ownership, and issues `fullchain.pem` + `privkey.pem` into `/etc/letsencrypt/live/snowfox.live/`.

---

### Step 4: Deploy Reverse Proxy Virtual Hosts
1. Copy the hardened configuration [`nginx-safe.conf`](nginx-safe.conf) to the container:
   ```bash
   cp nginx-safe.conf /etc/nginx/sites-available/snowfox-safe.conf
   ln -s /etc/nginx/sites-available/snowfox-safe.conf /etc/nginx/sites-enabled/
   rm -f /etc/nginx/sites-enabled/default
   ```
2. Test configuration and reload Nginx:
   ```bash
   nginx -t && systemctl reload nginx
   ```

---

### Step 5: Configure OpenWrt Split-Horizon DNS
Execute [`scripts/setup-split-dns-openwrt.sh`](scripts/setup-split-dns-openwrt.sh) on your OpenWrt router (`192.168.1.1`):
```bash
# 1. Whitelist snowfox.live from DNS Rebinding Protection
uci add_list dhcp.@dnsmasq[0].rebind_domain='snowfox.live'

# 2. Add local service records pointing to nginx-safe (10.10.10.10)
uci add_list dhcp.@dnsmasq[0].address='/pve.snowfox.live/10.10.10.10'
uci add_list dhcp.@dnsmasq[0].address='/router.snowfox.live/10.10.10.10'
uci add_list dhcp.@dnsmasq[0].address='/wan.snowfox.live/10.10.10.10'
uci add_list dhcp.@dnsmasq[0].address='/pihole.snowfox.live/10.10.10.10'
uci add_list dhcp.@dnsmasq[0].address='/gitea.snowfox.live/10.10.10.10'
uci add_list dhcp.@dnsmasq[0].address='/n8n.snowfox.live/10.10.10.10'
uci add_list dhcp.@dnsmasq[0].address='/short-admin.snowfox.live/10.10.10.10'
uci add_list dhcp.@dnsmasq[0].address='/ha.snowfox.live/10.10.10.10'

# 3. Commit and restart dnsmasq
uci commit dhcp
/etc/init.d/dnsmasq reload
```

---

### Step 6: Configure Pi-hole (Out-of-Band DNS Sinkhole)
On LXC 205 (`192.168.1.135`):
1. Enable `etc_dnsmasq_d` in `/etc/pihole/pihole.toml` so Pi-hole v6 reads drop-in configuration files:
   ```bash
   sed -i 's/etc_dnsmasq_d = false/etc_dnsmasq_d = true/' /etc/pihole/pihole.toml
   ```
2. Add the records to `/etc/dnsmasq.d/05-custom-snowfox.conf`:
```text
rebind-domain-ok=/snowfox.live/
address=/pve.snowfox.live/10.10.10.10
address=/router.snowfox.live/10.10.10.10
address=/wan.snowfox.live/10.10.10.10
address=/pihole.snowfox.live/10.10.10.10
address=/gitea.snowfox.live/10.10.10.10
address=/n8n.snowfox.live/10.10.10.10
address=/short-admin.snowfox.live/10.10.10.10
address=/photos.snowfox.live/10.10.10.10
address=/ha.snowfox.live/10.10.10.10
address=/internal.snowfox.live/10.10.10.10
```
3. Restart DNS engine:
```bash
systemctl restart pihole-FTL
```

---

## 🔍 3. Verification & Validation Audit

Run the following checks from your workstation (`192.168.1.197`):

### 1. Internal DNS Resolution Verification
```bash
# Query local OpenWrt router
nslookup gitea.snowfox.live 192.168.1.1
```
*Expected Output:*
```text
Server:         192.168.1.1
Address:        192.168.1.1#53

Name:   gitea.snowfox.live
Address: 10.10.10.10
```

### 2. Public DNS Isolation Verification (Zero Leak Test)
```bash
# Query public Google DNS from the outside
nslookup gitea.snowfox.live 8.8.8.8
```
*Expected Output:*
```text
** server can't find gitea.snowfox.live: NXDOMAIN
```
*(Confirms that no record exists on the public internet).*

### 3. TLS Handshake & Certificate SAN Verification
```bash
curl -vI https://pve.snowfox.live
```
*Expected Output:*
```text
* SSL connection using TLSv1.3 / TLS_AES_256_GCM_SHA384
* ALPN: server accepted http/1.1
* Server certificate:
*  subject: CN=*.snowfox.live
*  issuer: C=US; O=Let's Encrypt; CN=YR1
*  SSL certificate verify ok.
HTTP/1.1 200 OK
```

---

## 🛡️ 4. Security & Isolation Matrix

| Capability | Naive Public DNS (Rejected) | Split-Horizon DNS (Implemented) |
| :--- | :--- | :--- |
| **Public IP Leak** | ❌ Exposes `10.10.10.x` subnets in public DNS | ✅ **Zero Leakage** (`NXDOMAIN` to external callers) |
| **DNS Rebinding Risk** | ❌ Routers drop queries due to anti-rebinding | ✅ **Whitelisted locally** via `rebind_domain` |
| **Inbound Ports Required** | ❌ Requires port 80/443 forwarded for HTTP-01 | ✅ **Zero Inbound Ports** (Uses Cloudflare DNS-01 API) |
| **Port Numbers in URLs** | ❌ Still required (e.g. `:8006`, `:3000`) | ✅ **Standard Port 443** everywhere |
| **Certificate Trust** | ❌ Untrusted / Self-signed browser errors | ✅ **100% Valid Public CA** Green Padlock |

---

## 🛠️ 5. Engineering Post-Mortem: What, How, Why, Failures & Solves

> **Full Architectural Reference:** See [ADR-008 Section 5](../../knowledge/architecture-decisions.md#5-engineering-post-mortem-what-how-why-failures--solves).

### Summary Table: Problems Encountered & Exact Solves

| # | Encountered Issue | Root Cause | Implemented Engineering Solution | Status |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **Asymmetric TCP drop on Wi-Fi** | OpenWrt VM sent return SYN-ACK directly to workstation Wi-Fi MAC, bypassing physical router conntrack. | Added persistent `/etc/nftables.d/20-proxmox-zones-masq.nft` (`ip daddr 10.0.0.0/8 oifname "br-lan" masquerade`) on physical router. | 🟢 Solved |
| **2** | **RFC 3442 Option 121 cleared default gateway** | RFC 3442 mandates DHCP clients ignore Option 3 (gateway) when Option 121 is sent. | Included `0.0.0.0/0,192.168.1.1` in Option 121 alongside `10.0.0.0/8,192.168.1.129`. | 🟢 Solved |
| **3** | **Pi-hole v6 drop-in DNS config ignored** | Pi-hole v6 defaults to `etc_dnsmasq_d = false` in `/etc/pihole/pihole.toml`. | Set `etc_dnsmasq_d = true` and deployed `/etc/dnsmasq.d/05-custom-snowfox.conf`. | 🟢 Solved |
| **4** | **Browser `NET::ERR_CERT_AUTHORITY_INVALID`** | LXC 201 was running temporary bootstrap self-signed certificate. | Automated Let's Encrypt Wildcard certificate via Terraform [`iac/terraform/acme-wildcard`](../../iac/terraform/acme-wildcard). | 🟢 Solved |
| **5** | **Cloudflare R2 storage token rejected** | Token was generated under R2 Object Storage (with S3 credentials) rather than Account/Zone API Tokens. | Programmatically generated dedicated `Terraform-Homelab-Master` token using Global API Key, saved to Bitwarden. | 🟢 Solved |
| **6** | **Terraform JumpHost SSH authentication prompt** | `~/.ssh/config` matched `Host proxmox` but not literal IP `192.168.1.2`. | Updated `~/.ssh/config` to match both alias and IP with `id_rsa_gemini_codeberg`. | 🟢 Solved |

---

### Live Verification Matrix
All endpoints verified with strict public CA validation from workstation PC:
- `https://pve.snowfox.live` $\rightarrow$ `HTTP 200 OK` (Issuer: Let's Encrypt `YR1`)
- `https://router.snowfox.live` $\rightarrow$ `HTTP 200 OK` (LuCI Dashboard)
- `https://pihole.snowfox.live` $\rightarrow$ `HTTP 200 OK` (Pi-hole Dashboard)
- `https://wan.snowfox.live` $\rightarrow$ `HTTP 200 OK` (WAN Gateway Controller)
- `https://short-admin.snowfox.live` $\rightarrow$ `HTTP 200 OK` (URL Shortener Admin)

