#!/usr/bin/env python3
"""
Snowfox Short Links Manager - Private Internal Web Application (vmbr1)
Location: Proxmox LXC 225 (10.10.10.35 / short.internal.lab:8080)

Zero external pip dependencies: Runs entirely using standard library Python 3.
Connects outbound to Cloudflare Worker Edge via HTTPS.
"""

import http.server
import socketserver
import urllib.request
import urllib.error
import urllib.parse
import json
import os
import sys
import datetime
import re

PORT = int(os.environ.get("PORT", 8080))
HOST = os.environ.get("HOST", "0.0.0.0")
CLOUDFLARE_WORKER_URL = os.environ.get("CLOUDFLARE_WORKER_URL", "https://short.snowfox.live").rstrip("/")
SECRET_TOKEN = os.environ.get("SHORTENER_SECRET_TOKEN", "")

# Load .env file if present in current working directory
def load_env_file(path=".env"):
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and not os.environ.get(k):
                    os.environ[k] = v
    except Exception as e:
        sys.stderr.write(f"Warning: could not read {path}: {e}\n")

load_env_file()
CLOUDFLARE_WORKER_URL = os.environ.get("CLOUDFLARE_WORKER_URL", CLOUDFLARE_WORKER_URL).rstrip("/")
SECRET_TOKEN = os.environ.get("SHORTENER_SECRET_TOKEN", SECRET_TOKEN)

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>⚡ Short Link Manager · Snowfox Lab</title>
  <style>
    :root {
      --bg: #090d16;
      --card-bg: #111827;
      --card-sub: #1a2234;
      --border: #1f293d;
      --border-focus: #38bdf8;
      --text: #f8fafc;
      --muted: #94a3b8;
      --accent: #38bdf8;
      --accent-hover: #0284c7;
      --green: #22c55e;
      --red: #ef4444;
      --red-hover: #dc2626;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif; }
    body { background: var(--bg); color: var(--text); min-height: 100vh; padding: 2rem 1rem; display: flex; justify-content: center; }
    .app-container { width: 100%; max-width: 900px; }

    /* Header & Navigation */
    .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; border-bottom: 1px solid var(--border); padding-bottom: 1.25rem; flex-wrap: wrap; gap: 1rem; }
    .brand { display: flex; align-items: center; gap: 0.75rem; }
    .brand-icon { background: linear-gradient(135deg, #0284c7, #38bdf8); width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 1.25rem; }
    .brand-text h1 { font-size: 1.25rem; font-weight: 700; color: #fff; }
    .brand-text p { font-size: 0.8rem; color: var(--muted); }
    .zone-badge { background: rgba(34, 197, 94, 0.12); color: var(--green); border: 1px solid rgba(34, 197, 94, 0.25); font-size: 0.75rem; font-weight: 600; padding: 0.25rem 0.6rem; border-radius: 9999px; }

    /* Tab Switcher */
    .tabs { display: flex; background: var(--card-bg); border: 1px solid var(--border); border-radius: 10px; padding: 4px; gap: 4px; }
    .tab-btn { background: transparent; border: none; color: var(--muted); padding: 0.5rem 1rem; border-radius: 6px; font-size: 0.875rem; font-weight: 600; cursor: pointer; transition: all 0.2s ease; display: flex; align-items: center; gap: 0.4rem; }
    .tab-btn:hover { color: #fff; }
    .tab-btn.active { background: var(--accent); color: #000; box-shadow: 0 2px 4px rgba(0,0,0,0.3); }

    /* Cards */
    .card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 14px; padding: 2rem; margin-bottom: 2rem; box-shadow: 0 4px 12px rgba(0,0,0,0.25); }
    .card-title { font-size: 1.15rem; font-weight: 600; margin-bottom: 1.5rem; display: flex; align-items: center; gap: 0.5rem; color: #f1f5f9; }

    /* Form Fields */
    .form-group { margin-bottom: 1.25rem; }
    .form-label { display: block; font-size: 0.85rem; font-weight: 500; color: var(--muted); margin-bottom: 0.4rem; }
    .form-label span.opt { font-size: 0.75rem; opacity: 0.7; }
    .input-wrap { position: relative; display: flex; align-items: center; }
    .input-prefix { background: var(--card-sub); border: 1px solid var(--border); border-right: none; color: var(--muted); padding: 0.75rem 0.85rem; border-top-left-radius: 8px; border-bottom-left-radius: 8px; font-size: 0.9rem; font-family: monospace; }
    .input-field { width: 100%; background: var(--card-sub); border: 1px solid var(--border); border-radius: 8px; color: #fff; padding: 0.75rem 1rem; font-size: 0.95rem; transition: border-color 0.2s; outline: none; }
    .input-field.has-prefix { border-top-left-radius: 0; border-bottom-left-radius: 0; }
    .input-field:focus { border-color: var(--border-focus); box-shadow: 0 0 0 1px var(--border-focus); }

    /* Buttons */
    .btn { display: inline-flex; align-items: center; justify-content: center; gap: 0.5rem; padding: 0.75rem 1.5rem; border-radius: 8px; font-size: 0.95rem; font-weight: 600; cursor: pointer; transition: all 0.2s ease; border: none; }
    .btn-primary { background: var(--accent); color: #000; width: 100%; }
    .btn-primary:hover { background: var(--accent-hover); color: #fff; }
    .btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
    .btn-secondary { background: var(--card-sub); border: 1px solid var(--border); color: var(--text); padding: 0.45rem 0.8rem; font-size: 0.8rem; }
    .btn-secondary:hover { border-color: var(--accent); color: var(--accent); }
    .btn-danger { background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); color: var(--red); padding: 0.45rem 0.75rem; font-size: 0.8rem; border-radius: 6px; }
    .btn-danger:hover { background: var(--red); color: #fff; }

    /* Output Success Card */
    #output-card { display: none; background: rgba(56, 189, 248, 0.06); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 12px; padding: 1.5rem; margin-top: 1.5rem; animation: slideDown 0.3s ease; }
    .output-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; }
    .output-badge { font-size: 0.75rem; font-weight: 700; color: var(--green); text-transform: uppercase; letter-spacing: 0.5px; }
    .result-box { display: flex; gap: 0.5rem; margin-bottom: 0.75rem; }
    .result-input { flex: 1; background: #000; border: 1px solid var(--border); border-radius: 8px; color: #38bdf8; padding: 0.75rem 1rem; font-family: monospace; font-size: 1.05rem; font-weight: 600; }
    .copy-btn { background: var(--accent); color: #000; font-weight: 700; border-radius: 8px; padding: 0 1.25rem; cursor: pointer; border: none; font-size: 0.9rem; transition: all 0.2s ease; }
    .copy-btn:hover { background: #fff; }
    .output-meta { font-size: 0.825rem; color: var(--muted); display: flex; justify-content: space-between; }

    /* Page 2: Table & Search */
    .table-actions { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem; gap: 1rem; flex-wrap: wrap; }
    .search-input { background: var(--card-sub); border: 1px solid var(--border); border-radius: 8px; color: #fff; padding: 0.6rem 1rem; font-size: 0.875rem; width: 100%; max-width: 320px; outline: none; }
    .search-input:focus { border-color: var(--border-focus); }
    .links-table { width: 100%; border-collapse: collapse; text-align: left; font-size: 0.875rem; }
    .links-table th { background: var(--card-sub); color: var(--muted); font-weight: 600; padding: 0.75rem 1rem; border-bottom: 1px solid var(--border); text-transform: uppercase; font-size: 0.725rem; letter-spacing: 0.5px; }
    .links-table td { padding: 1rem; border-bottom: 1px solid var(--border); vertical-align: middle; }
    .links-table tr:hover { background: rgba(255, 255, 255, 0.02); }
    .slug-cell { font-family: monospace; font-weight: 600; color: var(--accent); }
    .dest-cell { max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--muted); }
    .date-cell { color: var(--muted); font-size: 0.8rem; white-space: nowrap; }
    .action-group { display: flex; gap: 0.5rem; justify-content: flex-end; }

    /* Alert Banners */
    .alert { padding: 0.85rem 1rem; border-radius: 8px; font-size: 0.875rem; margin-bottom: 1rem; display: none; }
    .alert-error { background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); color: #fca5a5; }
    .alert-success { background: rgba(34, 197, 94, 0.15); border: 1px solid rgba(34, 197, 94, 0.3); color: #86efac; }

    /* Empty state */
    .empty-state { text-align: center; padding: 3rem 1rem; color: var(--muted); }

    @keyframes slideDown { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }
    @media (max-width: 650px) {
      .header { flex-direction: column; align-items: flex-start; }
      .tabs { width: 100%; }
      .tab-btn { flex: 1; justify-content: center; }
      .dest-cell { max-width: 140px; }
    }
  </style>
</head>
<body>
  <div class="app-container">
    <!-- Header -->
    <header class="header">
      <div class="brand">
        <div class="brand-icon">⚡</div>
        <div class="brand-text">
          <h1>Snowfox Short Links</h1>
          <p>Cloudflare KV Edge Engine · Strict BD Geo-Fence</p>
        </div>
      </div>
      <div style="display: flex; align-items: center; gap: 0.75rem;">
        <span class="zone-badge">🔒 vmbr1 Safe Internal</span>
        <div class="tabs">
          <button class="tab-btn active" id="tab-btn-generator" onclick="switchPage('generator')">⚡ Generator</button>
          <button class="tab-btn" id="tab-btn-registry" onclick="switchPage('registry')">📋 All Links <span id="nav-count" style="opacity:0.75"></span></button>
        </div>
      </div>
    </header>

    <div id="alert-banner" class="alert"></div>

    <!-- PAGE 1: Link Generator -->
    <main id="page-generator" class="card">
      <h2 class="card-title">🔗 Create New Shortened Link</h2>
      <form id="shorten-form" onsubmit="handleCreateLink(event)">
        <div class="form-group">
          <label class="form-label">Destination URL *</label>
          <input type="url" id="dest-url" class="input-field" placeholder="https://github.com/snowfox-rubait/lab" required>
        </div>

        <div class="form-group">
          <label class="form-label">Custom Slug <span class="opt">(Optional - leaves blank to auto-generate 6 chars)</span></label>
          <div class="input-wrap">
            <span class="input-prefix">short.snowfox.live/</span>
            <input type="text" id="custom-slug" class="input-field has-prefix" placeholder="homelab" pattern="[a-zA-Z0-9_-]+" title="Only alphanumeric letters, dashes and underscores">
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">Title / Note <span class="opt">(Optional description for inventory)</span></label>
          <input type="text" id="link-title" class="input-field" placeholder="Homelab documentation repo">
        </div>

        <button type="submit" id="submit-btn" class="btn btn-primary">
          <span>⚡ Generate Short Link</span>
        </button>
      </form>

      <!-- Output Card -->
      <div id="output-card">
        <div class="output-header">
          <span class="output-badge">✓ Link Live at Edge</span>
          <span id="output-timestamp" style="font-size: 0.75rem; color: var(--muted);"></span>
        </div>
        <div class="result-box">
          <input type="text" id="output-link" class="result-input" readonly>
          <button type="button" class="copy-btn" id="copy-result-btn" onclick="copyToClipboard('output-link', this)">Copy</button>
        </div>
        <div class="output-meta">
          <span id="output-destination" style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:80%;"></span>
          <span style="color:var(--green);">BD Geo-Fenced</span>
        </div>
      </div>
    </main>

    <!-- PAGE 2: All Links Registry -->
    <main id="page-registry" class="card" style="display: none;">
      <div class="table-actions">
        <h2 class="card-title" style="margin-bottom:0;">📋 Shortened Links Registry</h2>
        <div style="display:flex; gap:0.5rem; align-items:center;">
          <input type="text" id="search-box" class="search-input" placeholder="🔍 Filter links..." oninput="filterLinks()">
          <button class="btn btn-secondary" onclick="fetchLinks(true)">🔄 Refresh</button>
        </div>
      </div>

      <div style="overflow-x: auto;">
        <table class="links-table">
          <thead>
            <tr>
              <th>Short Link</th>
              <th>Description / Title</th>
              <th>Destination URL</th>
              <th>Created</th>
              <th style="text-align: right;">Action</th>
            </tr>
          </thead>
          <tbody id="links-tbody">
            <!-- Dynamically populated -->
          </tbody>
        </table>
      </div>
      <div id="empty-state" class="empty-state" style="display: none;">
        No shortened links found. Create your first link in the Generator!
      </div>
    </main>
  </div>

  <script>
    let allLinks = [];

    // Switch between Page 1 and Page 2
    function switchPage(page) {
      const pageGen = document.getElementById("page-generator");
      const pageReg = document.getElementById("page-registry");
      const btnGen = document.getElementById("tab-btn-generator");
      const btnReg = document.getElementById("tab-btn-registry");

      if (page === 'registry') {
        pageGen.style.display = "none";
        pageReg.style.display = "block";
        btnGen.classList.remove("active");
        btnReg.classList.add("active");
        fetchLinks();
      } else {
        pageGen.style.display = "block";
        pageReg.style.display = "none";
        btnGen.classList.add("active");
        btnReg.classList.remove("active");
      }
    }

    // Handle Link Generation
    async function handleCreateLink(event) {
      event.preventDefault();
      showAlert("", "none");

      const submitBtn = document.getElementById("submit-btn");
      const destination = document.getElementById("dest-url").value.trim();
      const slug = document.getElementById("custom-slug").value.trim();
      const title = document.getElementById("link-title").value.trim();

      submitBtn.disabled = true;
      submitBtn.innerHTML = "<span>⏳ Connecting to Cloudflare KV...</span>";

      try {
        const res = await fetch("/api/create", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ destination, slug, title })
        });
        const data = await res.json();

        if (res.ok && data.success) {
          const outputCard = document.getElementById("output-card");
          const outputLink = document.getElementById("output-link");
          const outputDest = document.getElementById("output-destination");
          const outputTime = document.getElementById("output-timestamp");

          outputLink.value = data.short_url;
          outputDest.innerText = "Target: " + data.destination;
          outputTime.innerText = new Date().toLocaleTimeString();
          outputCard.style.display = "block";

          showAlert("Short link generated successfully and active on Cloudflare Edge!", "success");
          fetchLinks(); // Refresh background cache
        } else {
          const errMsg = data.details ? `${data.error} (${data.details})` : (data.error || "Failed to create short link.");
          showAlert(errMsg, "error");
        }
      } catch (err) {
        showAlert("Network error connecting to management daemon: " + err.message, "error");
      } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = "<span>⚡ Generate Short Link</span>";
      }
    }

    // Fetch All Links from KV
    async function fetchLinks(manual = false) {
      const tbody = document.getElementById("links-tbody");
      const empty = document.getElementById("empty-state");

      try {
        const res = await fetch("/api/links");
        const data = await res.json();

        if (res.ok && data.links) {
          allLinks = data.links;
          document.getElementById("nav-count").innerText = `(${allLinks.length})`;
          renderLinksTable(allLinks);
          if (manual) showAlert("Registry synchronized with Cloudflare KV.", "success");
        } else {
          const errMsg = data.details ? `${data.error} (${data.details})` : (data.error || "Failed to fetch registry.");
          showAlert(errMsg, "error");
        }
      } catch (err) {
        showAlert("Error loading links: " + err.message, "error");
      }
    }

    // Render Table Rows
    function renderLinksTable(links) {
      const tbody = document.getElementById("links-tbody");
      const empty = document.getElementById("empty-state");
      tbody.innerHTML = "";

      if (!links || links.length === 0) {
        empty.style.display = "block";
        return;
      }
      empty.style.display = "none";

      links.forEach(item => {
        const tr = document.createElement("tr");
        const shortUrl = item.short_url || `https://short.snowfox.live/${item.slug}`;
        const createdDate = item.created_at ? new Date(item.created_at).toLocaleDateString() : "-";

        tr.innerHTML = `
          <td class="slug-cell">/${escapeHtml(item.slug)}</td>
          <td>${escapeHtml(item.title || "—")}</td>
          <td class="dest-cell" title="${escapeHtml(item.destination)}">
            <a href="${escapeHtml(item.destination)}" target="_blank" rel="noopener" style="color:inherit;text-decoration:none;">
              ${escapeHtml(item.destination)} ↗
            </a>
          </td>
          <td class="date-cell">${createdDate}</td>
          <td style="text-align: right;">
            <div class="action-group">
              <button class="btn btn-secondary" onclick="copyText('${escapeHtml(shortUrl)}', this)">Copy</button>
              <button class="btn btn-danger" onclick="deleteLink('${escapeHtml(item.slug)}')">Delete</button>
            </div>
          </td>
        `;
        tbody.appendChild(tr);
      });
    }

    // Filter Links
    function filterLinks() {
      const q = document.getElementById("search-box").value.toLowerCase();
      const filtered = allLinks.filter(l => 
        (l.slug && l.slug.toLowerCase().includes(q)) ||
        (l.destination && l.destination.toLowerCase().includes(q)) ||
        (l.title && l.title.toLowerCase().includes(q))
      );
      renderLinksTable(filtered);
    }

    // Delete Short Link
    async function deleteLink(slug) {
      if (!confirm(`Are you sure you want to delete short link '/${slug}'? It will immediately stop redirecting.`)) {
        return;
      }

      try {
        const res = await fetch("/api/delete", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ slug })
        });
        const data = await res.json();
        if (res.ok && data.success) {
          showAlert(`Short link '/${slug}' successfully removed from Cloudflare KV.`, "success");
          fetchLinks();
        } else {
          const errMsg = data.details ? `${data.error} (${data.details})` : (data.error || "Failed to delete link.");
          showAlert(errMsg, "error");
        }
      } catch (err) {
        showAlert("Error deleting link: " + err.message, "error");
      }
    }

    // Copy to clipboard helper
    function copyToClipboard(elementId, btn) {
      const input = document.getElementById(elementId);
      copyText(input.value, btn);
    }

    function copyText(text, btn) {
      navigator.clipboard.writeText(text).then(() => {
        const orig = btn.innerText;
        btn.innerText = "Copied! ✨";
        btn.style.background = "#22c55e";
        btn.style.color = "#000";
        setTimeout(() => {
          btn.innerText = orig;
          btn.style.background = "";
          btn.style.color = "";
        }, 1800);
      }).catch(err => {
        alert("Failed to copy: " + err);
      });
    }

    // Alert display
    function showAlert(msg, type) {
      const banner = document.getElementById("alert-banner");
      if (!msg || type === "none") {
        banner.style.display = "none";
        return;
      }
      banner.innerText = msg;
      banner.className = `alert alert-${type}`;
      banner.style.display = "block";
      if (type === "success") {
        setTimeout(() => { banner.style.display = "none"; }, 5000);
      }
    }

    function escapeHtml(str) {
      if (!str) return "";
      return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
    }

    // Initial load
    fetchLinks();
  </script>
</body>
</html>
"""

class ShortManagerHandler(http.server.BaseHTTPRequestHandler):
    server_version = "SnowfoxShortManager/1.0"

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)

        # Healthcheck endpoint
        if url.path == "/health":
            self.send_json_response(200, {
                "status": "healthy",
                "zone": "vmbr1",
                "worker_url": CLOUDFLARE_WORKER_URL,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
            })
            return

        # API: List all links
        if url.path == "/api/links":
            self.handle_api_proxy_get()
            return

        # Serve UI for root or /links
        if url.path in ["/", "/links", "/generator"]:
            self.send_html_response(200, HTML_PAGE)
            return

        self.send_error(404, "Page Not Found")

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)

        # API: Create link
        if url.path == "/api/create":
            self.handle_api_proxy_create()
            return

        # API: Delete link
        if url.path == "/api/delete":
            self.handle_api_proxy_delete()
            return

        self.send_error(404, "Endpoint Not Found")

    def handle_api_proxy_create(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length <= 0:
            self.send_json_response(400, {"error": "Missing request body"})
            return

        body = self.rfile.read(content_length)
        target_url = f"{CLOUDFLARE_WORKER_URL}/api/shorten"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {SECRET_TOKEN}",
            "User-Agent": "SnowfoxShortManager-vmbr1"
        }

        try:
            req = urllib.request.Request(target_url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
                self.send_raw_response(resp.status, "application/json", data)
        except urllib.error.HTTPError as e:
            err_data = e.read()
            sys.stderr.write(f"[ERROR] POST {target_url} returned HTTP {e.code}: {err_data.decode('utf-8', 'ignore')}\n")
            sys.stderr.flush()
            self.send_raw_response(e.code, "application/json", err_data)
        except Exception as e:
            sys.stderr.write(f"[ERROR] POST {target_url} failed: {e}\n")
            sys.stderr.flush()
            self.send_json_response(502, {"error": f"Failed to connect to Cloudflare Worker: {str(e)}"})

    def handle_api_proxy_get(self):
        target_url = f"{CLOUDFLARE_WORKER_URL}/api/list"
        headers = {
            "Authorization": f"Bearer {SECRET_TOKEN}",
            "User-Agent": "SnowfoxShortManager-vmbr1"
        }

        try:
            req = urllib.request.Request(target_url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
                self.send_raw_response(resp.status, "application/json", data)
        except urllib.error.HTTPError as e:
            err_data = e.read()
            sys.stderr.write(f"[ERROR] GET {target_url} returned HTTP {e.code}: {err_data.decode('utf-8', 'ignore')}\n")
            sys.stderr.flush()
            self.send_raw_response(e.code, "application/json", err_data)
        except Exception as e:
            sys.stderr.write(f"[ERROR] GET {target_url} failed: {e}\n")
            sys.stderr.flush()
            self.send_json_response(502, {"error": f"Failed to reach Cloudflare Worker: {str(e)}"})

    def handle_api_proxy_delete(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length <= 0:
            self.send_json_response(400, {"error": "Missing slug in body"})
            return

        body = self.rfile.read(content_length)
        try:
            payload = json.loads(body.decode("utf-8"))
            slug = payload.get("slug", "").strip()
        except Exception:
            self.send_json_response(400, {"error": "Invalid JSON body"})
            return

        if not slug:
            self.send_json_response(400, {"error": "Missing slug parameter"})
            return

        target_url = f"{CLOUDFLARE_WORKER_URL}/api/delete/{urllib.parse.quote(slug)}"
        headers = {
            "Authorization": f"Bearer {SECRET_TOKEN}",
            "User-Agent": "SnowfoxShortManager-vmbr1"
        }

        try:
            req = urllib.request.Request(target_url, headers=headers, method="DELETE")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
                self.send_raw_response(resp.status, "application/json", data)
        except urllib.error.HTTPError as e:
            err_data = e.read()
            sys.stderr.write(f"[ERROR] DELETE {target_url} returned HTTP {e.code}: {err_data.decode('utf-8', 'ignore')}\n")
            sys.stderr.flush()
            self.send_raw_response(e.code, "application/json", err_data)
        except Exception as e:
            sys.stderr.write(f"[ERROR] DELETE {target_url} failed: {e}\n")
            sys.stderr.flush()
            self.send_json_response(502, {"error": f"Failed to reach Cloudflare Worker: {str(e)}"})

    def send_html_response(self, status, content):
        data = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(data)

    def send_json_response(self, status, obj):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_raw_response(self, status, content_type, data):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        # Concise logging to stdout
        sys.stdout.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {self.client_address[0]} - {format % args}\n")

if __name__ == "__main__":
    print(f"⚡ Starting Snowfox Short Links Manager on {HOST}:{PORT}")
    print(f"🔒 Target Cloudflare Worker: {CLOUDFLARE_WORKER_URL}")
    print(f"🛡️  Secret Token configured: {'Yes' if SECRET_TOKEN else 'No (set SHORTENER_SECRET_TOKEN)'}")

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((HOST, PORT), ShortManagerHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down Short Links Manager.")
