# 🔗 Project 13: Personal URL Shortener (`short.snowfox.live`)

> **Project ID:** `13-personal-url-shortener`  
> **Status:** Planned / Architecture & Implementation Specification  
> **Target Public Domain:** `https://short.snowfox.live/abcdxyz`  
> **Target Management Web UI:** Safe Internal Zone (`vmbr1`, `10.10.10.35` / `short.internal.lab`)  
> **Security Model:** **Strict Geo-Fencing** (Bangladesh Only) + **Air-Gapped Private Admin UI** (`vmbr1`) + **Serverless 24/7 Edge Redirection** (Cloudflare Workers + KV)

---

## 🎯 1. Overview & Core Requirements

This project delivers a personal, high-performance URL shortening platform with strict geographic access controls and total administrative privacy:
1. **Branded Public Short URLs:** Short, memorable URLs under `https://short.snowfox.live/slug` for resumes, social media, documentation, and sharing.
2. **Bangladesh-Only Geo-Fence (`BD`):** Redirection links are strictly restricted to visitors located within Bangladesh. Requests originating from outside Bangladesh are terminated immediately at Cloudflare's edge.
3. **24/7/365 Edge Availability:** Operates independently of the Proxmox ThinkPad server's nightly power schedule (offline 00:00–07:00 AM per `power-manager.sh`). Public links never experience downtime.
4. **Air-Gapped Private Management UI in `vmbr1`:** A clean, dedicated 2-page web application hosted entirely within the **Safe Internal Zone (`vmbr1`)** with **zero public internet ingress**.
5. **Outbound-Only Cloudflare Synchronization:** The management website communicates with Cloudflare's API strictly via **outbound HTTPS**, ensuring the administration portal is invisible and unreachable to external scanners.

---

## 🏗️ 2. Dual-Tier System Architecture

```
═════════════════════════════════════════════════════════════════════════════════════════════
                       TIER 1: 24/7 GLOBAL EDGE (CLOUDFLARE)
═════════════════════════════════════════════════════════════════════════════════════════════
                                   │
                    Public Visitor │ (GET https://short.snowfox.live/xyz)
                                   ▼
                   ┌───────────────────────────────┐
                   │  Cloudflare Edge WAF / Worker │
                   └───────────────┬───────────────┘
                                   │
              ┌────────────────────┴────────────────────┐
              │                                         │
        [ Country != "BD" ]                       [ Country == "BD" ]
              │                                         │
              ▼                                         ▼
   HTTP 403 Forbidden                        Cloudflare KV Store Lookup
   "Access Restricted to BD"                  Key: "xyz" ➔ Target URL
                                                        │
                                                        ▼
                                             HTTP 302 Redirect to Target
                                             (<15ms Response Time)

═════════════════════════════════════════════════════════════════════════════════════════════
               TIER 2: PRIVATE INTERNAL MANAGEMENT (HOMELAB vmbr1)
═════════════════════════════════════════════════════════════════════════════════════════════

   Owner Workstation (192.168.1.197) / Tailscale
        │
        │ HTTP (LAN Only - No Public DNS)
        ▼
   ┌───────────────────────────────────────────────┐
   │  Shortener Web UI (LXC on vmbr1: 10.10.10.35) │
   │  - Page 1: Link Generator & Output Card       │
   │  - Page 2: Master Short Link Registry Table   │
   └───────────────────────┬───────────────────────┘
                           │
                           │ Outbound HTTPS API (Bearer Token / Secret Key)
                           │ (Permitted via OpenWrt VM NAT forwarding)
                           ▼
              Cloudflare KV API Endpoint
              (Pushes new slugs / Fetches all links / Deletes entries)
```

---

## 🌐 3. Tier 1: Cloudflare Edge Worker & Geo-Fencing Engine

### 3.1 Edge Worker Logic & Bangladesh Geo-Fencing
The Cloudflare Worker intercepts all incoming HTTP requests to `short.snowfox.live`:

```javascript
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const country = request.cf?.country;

    // 1. Enforce Strict Bangladesh-Only Geo-Fence
    if (country !== "BD") {
      return new Response(
        `<!DOCTYPE html>
        <html>
        <head><title>Access Restricted</title></head>
        <body style="font-family:sans-serif;text-align:center;padding:4rem;background:#0f172a;color:#f8fafc;">
          <h1 style="color:#ef4444;">🚫 Access Restricted</h1>
          <p>This redirection service is strictly restricted to visitors within Bangladesh.</p>
        </body>
        </html>`,
        {
          status: 403,
          headers: { "Content-Type": "text/html; charset=utf-8" }
        }
      );
    }

    // 2. Handle Management API Requests (Strictly Authenticated)
    if (url.pathname.startsWith("/api/")) {
      const authHeader = request.headers.get("Authorization");
      if (!authHeader || authHeader !== `Bearer ${env.SHORTENER_SECRET_TOKEN}`) {
        return new Response(JSON.stringify({ error: "Unauthorized" }), { status: 401 });
      }

      // API Routes for vmbr1 Management Dashboard
      if (request.method === "POST" && url.pathname === "/api/shorten") {
        const { slug, destination, title } = await request.json();
        await env.SHORT_LINKS.put(slug, destination, {
          metadata: { title, created_at: Date.now(), clicks: 0 }
        });
        return new Response(JSON.stringify({ success: true, short_url: `https://short.snowfox.live/${slug}` }), { status: 201 });
      }

      if (request.method === "GET" && url.pathname === "/api/list") {
        const list = await env.SHORT_LINKS.list();
        return new Response(JSON.stringify(list), { status: 200 });
      }

      if (request.method === "DELETE" && url.pathname.startsWith("/api/delete/")) {
        const slugToDelete = url.pathname.replace("/api/delete/", "");
        await env.SHORT_LINKS.delete(slugToDelete);
        return new Response(JSON.stringify({ success: true }), { status: 200 });
      }

      return new Response(JSON.stringify({ error: "Not Found" }), { status: 404 });
    }

    // 3. Handle Public Redirection (GET /slug)
    const slug = url.pathname.slice(1);
    if (!slug) {
      // Root access redirects safely to main personal portfolio
      return Response.redirect("https://snowfox.live", 302);
    }

    const destination = await env.SHORT_LINKS.get(slug);
    if (destination) {
      return Response.redirect(destination, 302);
    }

    return new Response("Short link not found", { status: 404 });
  }
};
```

---

## 🖥️ 4. Tier 2: Private Management Web Application (`vmbr1`)

### 4.1 Why `vmbr1` (Safe Internal) is Ideal
1. **Zero Public Attack Surface:** `vmbr1` is quarantined from the public internet by OpenWrt VM's firewall (`input: DROP`, `forward: DROP` for inbound traffic).
2. **Outbound Communication Feasibility:** OpenWrt allows outbound NAT routing from `vmbr1` to WAN. The web application can query `https://short.snowfox.live/api/...` or `https://api.cloudflare.com` over outbound HTTPS without requiring any open ports or reverse proxy tunnels into `vmbr1`.
3. **Internal Access:** Accessible on your local network via internal DNS (`http://short.internal.lab` or `http://10.10.10.35:8080`) or through your Tailscale network.

### 4.2 Web Application Structure (2 Pages / Views)

```
┌────────────────────────────────────────────────────────────────────────┐
│  ⚡ Snowfox Short Links Manager                [ Generator ] [ All Links ] │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│   Page 1: Link Generator                                               │
│   ───────────────────────────────────────────────────────────          │
│   Destination URL: [ https://github.com/snowfox-rubait/lab           ] │
│   Custom Slug:     [ lab-notebook        ] (Optional - auto-generates) │
│   Link Description:[ Homelab Engineering Repo                        ] │
│                                                                        │
│   [ ⚡ Shorten URL ]                                                   │
│                                                                        │
│   ┌──────────────────────────────────────────────────────────────┐     │
│   │ Result: https://short.snowfox.live/lab-notebook      [Copy]  │     │
│   └──────────────────────────────────────────────────────────────┘     │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────┐
│  ⚡ Snowfox Short Links Manager                [ Generator ] [ All Links ] │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│   Page 2: All Shortened URLs (Master Registry)                         │
│   ───────────────────────────────────────────────────────────          │
│   Search: [ Filter links... ]                                          │
│                                                                        │
│   Short Link          Destination                  Created      Action │
│   ─────────────────── ──────────────────────────── ──────────── ────── │
│   /lab-notebook       github.com/snowfox-rubait/lab 2026-10-29   [Del] │
│   /resume             drive.google.com/file/...    2026-10-25   [Del] │
│   /blog               snowfox.live/notes           2026-10-20   [Del] │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

#### Tech Stack:
- **Backend:** Lightweight Python (FastAPI / Flask) or Go single-binary container.
- **Frontend:** Responsive, clean dark-mode HTML/CSS/Vanilla JS (matches the sleek UI design of WAN Controller LXC 200).
- **Footprint:** **< 30 MB RAM**, minimal CPU usage.

---

## 🔒 5. Security & Threat Modeling

1. **Strict Bangladesh Geo-Fence Defense-in-Depth:**
   - **Layer 1 (Cloudflare WAF Custom Rule):** Rule expression `(http.host eq "short.snowfox.live" and ip.geoip.country ne "BD")` configured with action `Block`.
   - **Layer 2 (Worker Runtime Check):** `request.cf.country !== "BD"` evaluated at runtime before any KV read is executed.
2. **Secret Token Isolation:**
   - The master authorization token (`SHORTENER_SECRET_TOKEN`) is stored as an encrypted secret in Cloudflare Worker environment variables and mounted via `.env` in the private `vmbr1` web UI.
   - It is never exposed in client-side JavaScript or public HTTP responses.
3. **No Unauthenticated Link Creation:**
   - Public visitors have zero access to link creation APIs. Attempted POST/DELETE requests without the master bearer token receive `401 Unauthorized`.

---

## 📋 6. Phased Implementation Plan

- [ ] **Phase 1: Cloudflare DNS & Worker Scaffolding**
  - Add DNS record for `short.snowfox.live` in Cloudflare (Proxied `Orange Cloud`).
  - Configure Cloudflare WAF rule restricting `short.snowfox.live` strictly to Bangladesh (`BD`).
  - Deploy edge worker script with KV namespace `SHORT_LINKS`.
- [ ] **Phase 2: Management Web UI Development (`short-manager`)**
  - Build 2-page lightweight Python FastAPI web service (Page 1: Link Generator, Page 2: Link List Registry).
  - Test outbound Cloudflare KV API communication over `vmbr1`.
- [ ] **Phase 3: Proxmox LXC Deployment & Internal DNS**
  - Deploy container on Proxmox host inside `vmbr1` (`10.10.10.35`).
  - Add internal FQDN `short.internal.lab` into Pi-hole / OpenWrt `dnsmasq` local records.
- [ ] **Phase 4: End-to-End Verification**
  - Verify link generation from internal UI.
  - Test public resolution inside Bangladesh (`200 OK / 302 Redirect`).
  - Test external IP resolution via international VPN to confirm `403 Forbidden` geo-block.
