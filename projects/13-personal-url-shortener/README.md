# 🔗 Project 13: Personal URL Shortener (`short.snowfox.live`)

> **Project ID:** `13-personal-url-shortener`  
> **Status:** Planned / Architecture & Evaluation Blueprint  
> **Target Domain:** `https://short.snowfox.live/abcdxyz`  
> **Access Model:** **Private Administration** (User-only creation/management) + **Public Redirection** (Unrestricted global access)  
> **Primary Evaluation:** Cloudflare Workers + KV (Serverless Edge) vs. Self-Hosted Shlink (Proxmox LXC + PostgreSQL)

---

## 🎯 1. Overview & Core Requirements

This project establishes a personal, branded short-link redirection service under `short.snowfox.live`:
1. **Branded Custom Links:** Short, recognizable links for sharing across social platforms, documentation, messaging, and personal portfolios (e.g. `https://short.snowfox.live/git`, `https://short.snowfox.live/notes`).
2. **Strict Single-User Administration:** Only the owner can generate, edit, or delete short links. The creation interface and API must be strictly authenticated.
3. **Universal Public Redirection:** Anyone in the world clicking a short link must be redirected to the target destination instantly with zero authentication or friction.
4. **Homelab Uptime Constraint Awareness:** Must account for the Proxmox ThinkPad server's nightly power schedule (offline 00:00–07:00 AM per `power-manager.sh`). Public short links cannot suffer 7 hours of daily downtime.

---

## ⚖️ 2. Architectural Comparison: Options Evaluated

| Architecture Option | Hosting Location | Database / Storage | 24/7 Availability (Server Sleep) | RAM / Host Impact | Management Interface | Recommendation |
| :--- | :--- | :--- | :---: | :---: | :--- | :--- |
| **Option A: Cloudflare Workers + KV** | Cloudflare Global Edge (275+ PoPs) | Cloudflare KV (Key-Value) | ✅ **100% 24/7 Uptime** | **0 MiB (Serverless)** | REST API, Web UI, Telegram Bot | 🏆 **Top Recommendation (Zero-Downtime)** |
| **Option B: Self-Hosted Shlink** | Proxmox LXC (`vmbr2`) via Cloudflare Tunnel | PostgreSQL 17 on `db-central` (`vmbr7`) | ⚠️ **Offline 00:00–07:00** | ~150–250 MiB (PHP/Swoole) | Shlink Web Client (Official GUI) | 🥈 **Best for Deep Analytics** |
| **Option C: YOURLS** | Proxmox LXC (`vmbr2`) | MySQL / MariaDB | ⚠️ **Offline 00:00–07:00** | ~350 MiB (Apache + MariaDB) | Classic Admin Portal | ❌ **Rejected (Requires separate MariaDB)** |

---

## 🏗️ 3. Detailed Architectural Designs

### Approach 1: Cloudflare Workers + KV (Serverless Edge Architecture - Recommended)

```
[ Public Visitor ] ──────────────► [ Cloudflare Edge: short.snowfox.live/slug ]
                                                      │
                                                      ├── 1. KV Store Lookup ("slug" ➔ "https://target...")
                                                      └── 2. Return HTTP 301/302 Redirect (<15ms latency)

[ Owner Only ] ──────────────────► [ POST /api/shorten (Bearer Token) / Telegram Bot ]
                                                      │
                                                      └── Write new entry to Cloudflare KV
```

#### Why This Is the Best Engineering Fit for This Lab:
1. **Immunity to Server Sleep:** When the ThinkPad laptop powers down at midnight for battery health and silent night operation, public short links remain 100% functional worldwide.
2. **Zero Resource Overhead:** Consumes 0 MB of RAM on the 8GB ThinkPad host, preserving memory for heavy internal workloads (Gitea, Immich, n8n, Database).
3. **Ultra-Low Latency:** Redirection occurs at Cloudflare's nearest edge data center (<15ms) rather than traversing residential ISP PPPoE or Cloudflare Tunnel hops.
4. **Strict Private Creation:** 
   - Public requests (`GET /:slug`) only execute read operations against the KV store.
   - Admin routes (`POST /api/shorten`, `DELETE /api/:slug`) require an `Authorization: Bearer <SECRET_TOKEN>` header matching an environment secret in Cloudflare.
   - Creation can be triggered directly from an interactive command in the Telegram Bot Hub (`/short https://example.com custom_slug`) or an n8n webhook.

---

### Approach 2: Self-Hosted Shlink on Proxmox (`vmbr2` Public Ingress)

If advanced self-hosted analytics (browser breakdown, OS telemetry, referrer graphs, and total data sovereignty) are preferred:

```
[ Public Internet ] ──► [ Cloudflare Tunnel ] ──► [ nginx-public (LXC 202) ] ──► [ Shlink (LXC 225) ]
                                                                                         │
                                                                           TCP: 5432 (TLS / SCRAM)
                                                                                         ▼
                                                                              [ db-central (LXC 210) ]
```

1. **Target Subnet:** Public Ingress Zone (`vmbr2` at `10.20.20.25`).
2. **Database Integration:** Connects across the audited inter-bridge pinhole to `db-central` (`10.70.70.10:5432`) utilizing a dedicated database `shlink_db` and role `shlink_user`.
3. **Ingress Security:** 
   - Cloudflare Tunnel routes `short.snowfox.live` into `nginx-public` (`10.20.20.10`).
   - Public redirection routes (`GET /{shortCode}`) are open to all.
   - Admin REST API (`/rest/v3/*`) is protected via Shlink API Keys.
   - Shlink Web Client (admin dashboard) is restricted via IP allowlist or Cloudflare Zero Trust Access.
4. **Nightly Downtime Workaround:** To prevent broken links between 00:00 and 07:00 AM, Cloudflare Edge Cache Rules must be configured to cache `HTTP 301 Moved Permanently` responses for 24 hours at the edge.

---

## 🔒 4. Access Control & Security Policies

1. **Anti-Spam & Zero Public Creation:**
   - Public anonymous link creation is strictly disabled.
   - If an unauthenticated user navigates to `https://short.snowfox.live/`, they receive a clean static landing page or redirect to your root site (`https://snowfox.live`), with no exposed creation forms.
2. **Brute-Force & Enumeration Resistance:**
   - Slugs generated with high entropy (e.g. 6–7 character alphanumeric base62 strings = >3.5 trillion combinations).
   - Rate limiting enforced at Cloudflare Edge (WAF rate limit: max 60 requests/minute per IP).
3. **Audit Logging:**
   - All link creation events logged with timestamp, user ID, target destination, and assigned slug.

---

## 📋 5. Implementation Roadmap

- [ ] **Phase 1: Domain & Route Configuration**
  - Allocate DNS CNAME / route for `short.snowfox.live` in Cloudflare dashboard.
- [ ] **Phase 2: Deploy Edge Redirection Worker**
  - Scaffold Cloudflare Worker script with KV binding `SHORT_LINKS`.
  - Implement token-authenticated `POST /api/shorten` endpoint.
- [ ] **Phase 3: Client Integration**
  - Create Telegram bot command `/short <url>` inside Project 09 (Telegram Bot Hub).
  - Optional: WebUI dashboard protected via Cloudflare Access or local dashboard.
- [ ] **Phase 4: Optional Shlink Migration**
  - If detailed analytics are required, evaluate deploying Shlink in LXC on `vmbr2` connected to `db-central` with 24h Cloudflare edge cache rules.
