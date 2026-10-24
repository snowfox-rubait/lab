import http.server, socketserver, json, subprocess, urllib.parse

PORT = 8080

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Homelab WAN Gateway</title>
    <style>
        :root {
            --bg: #0f172a;
            --card: #1e293b;
            --text: #f8fafc;
            --muted: #94a3b8;
            --accent: #38bdf8;
            --green: #22c55e;
            --border: #334155;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: system-ui, -apple-system, sans-serif; }
        body { background: var(--bg); color: var(--text); padding: 2.5rem 1rem; display: flex; justify-content: center; }
        .container { width: 100%; max-width: 680px; }
        .header { margin-bottom: 2rem; text-align: center; }
        .header h1 { font-size: 1.8rem; color: var(--accent); margin-bottom: 0.5rem; }
        .header p { color: var(--muted); font-size: 0.95rem; }
        .card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2); }
        .card-title { font-size: 1.1rem; font-weight: 600; margin-bottom: 1rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; display: flex; justify-content: space-between; align-items: center; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem; }
        .stat-box { background: rgba(15, 23, 42, 0.6); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; }
        .stat-label { font-size: 0.8rem; color: var(--muted); margin-bottom: 0.25rem; }
        .stat-val { font-size: 1.05rem; font-weight: 600; display: flex; align-items: center; gap: 0.5rem; }
        .dot { width: 10px; height: 10px; border-radius: 50%; }
        .dot-green { background: var(--green); box-shadow: 0 0 8px var(--green); }
        .dot-gray { background: var(--muted); }
        .console-box { background: #000; border: 1px solid var(--border); border-radius: 8px; padding: 1rem; font-family: monospace; font-size: 0.85rem; color: #a7f3d0; white-space: pre-wrap; max-height: 160px; overflow-y: auto; }
        .actions { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; }
        button { background: var(--card); color: var(--text); border: 1px solid var(--accent); padding: 0.85rem 1rem; border-radius: 8px; font-weight: 600; cursor: pointer; transition: all 0.2s ease; display: flex; flex-direction: column; align-items: center; gap: 0.25rem; }
        button:hover { background: var(--accent); color: #000; transform: translateY(-2px); }
        button span.sub { font-size: 0.75rem; font-weight: normal; opacity: 0.85; }
        .refresh-btn { background: transparent; border: 1px solid var(--border); color: var(--muted); font-size: 0.8rem; padding: 0.3rem 0.6rem; border-radius: 6px; cursor: pointer; }
        #loading { display: none; text-align: center; color: var(--accent); font-weight: 600; margin-top: 1rem; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚡ Homelab WAN Gateway</h1>
            <p>VLAN 100 Multi-Mode Controller · TP-Link Archer C6 & Proxmox OpenWrt</p>
        </div>

        <div class="card">
            <div class="card-title">
                <span>Live Link Telemetry</span>
                <button class="refresh-btn" onclick="fetchStatus()">⟳ Refresh</button>
            </div>
            <div class="grid">
                <div class="stat-box">
                    <div class="stat-label">Physical Router (br-wan)</div>
                    <div class="stat-val" id="router-status"><span class="dot dot-gray"></span> Checking...</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">OpenWrt VM 100 (VLAN 100)</div>
                    <div class="stat-val" id="vm-status"><span class="dot dot-gray"></span> Checking...</div>
                </div>
            </div>
            <div class="stat-label">Raw Kernel Routing & Carrier:</div>
            <div class="console-box" id="raw-output">Connecting to router telemetry...</div>
        </div>

        <div class="card">
            <div class="card-title">Switch Mode</div>
            <div class="actions">
                <button onclick="setMode(1)">
                    Mode 1
                    <span class="sub">Physical Main</span>
                </button>
                <button onclick="setMode(2)">
                    Mode 2
                    <span class="sub">OpenWrt VM Main</span>
                </button>
                <button onclick="setMode(3)">
                    Mode 3
                    <span class="sub">Dual Active</span>
                </button>
            </div>
            <div id="loading">⏳ Applying mode switch & executing safety watchdog...</div>
        </div>
    </div>

    <script>
        async function fetchStatus() {
            try {
                const res = await fetch("/api/status");
                const data = await res.json();
                document.getElementById("raw-output").textContent = data.output;
                
                const rOnline = data.output.indexOf('Physical Router WAN (br-wan): "up": true') !== -1;
                const vOnline = data.output.indexOf('OpenWrt VM WAN (VLAN 100):   "up": true') !== -1;
                
                document.getElementById("router-status").innerHTML = rOnline 
                    ? '<span class="dot dot-green"></span> Online (PPPoE Active)' 
                    : '<span class="dot dot-gray"></span> Standby / Idle';
                    
                document.getElementById("vm-status").innerHTML = vOnline 
                    ? '<span class="dot dot-green"></span> Online (PPPoE Active)' 
                    : '<span class="dot dot-gray"></span> Standby / Idle';
            } catch(e) {
                document.getElementById("raw-output").textContent = "Error fetching status: " + e;
            }
        }

        async function setMode(mode) {
            if(!confirm("Switch to Mode " + mode + "?")) return;
            document.getElementById("loading").style.display = "block";
            try {
                const res = await fetch("/api/set", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ mode: mode.toString() })
                });
                const data = await res.json();
                document.getElementById("raw-output").textContent = data.output;
            } catch(e) {
                alert("Request failed: " + e);
            } finally {
                document.getElementById("loading").style.display = "none";
                fetchStatus();
            }
        }

        fetchStatus();
        setInterval(fetchStatus, 4000);
    </script>
</body>
</html>
"""

socketserver.TCPServer.allow_reuse_address = True

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/status":
            try:
                out = subprocess.check_output(["ssh", "root@192.168.1.1", "wan-mode", "status"], stderr=subprocess.STDOUT, timeout=6).decode()
            except Exception as e:
                out = str(e)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"output": out}).encode())
        elif parsed.path == "/api/set":
            # State-changing operations via GET are strictly rejected to prevent CSRF
            self.send_response(405)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Method Not Allowed. State mutations must use POST."}).encode())
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(HTML.encode())

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/set":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode() if content_length > 0 else ""
            
            mode = None
            # Support JSON payload
            try:
                data = json.loads(body)
                mode = str(data.get("mode", ""))
            except Exception:
                pass

            # Fallback to query parameter or form-encoded
            if not mode:
                params = urllib.parse.parse_qs(body or parsed.query)
                mode = params.get("mode", [""])[0]

            if mode in ["1", "2", "3"]:
                try:
                    out = subprocess.check_output(["ssh", "root@192.168.1.1", "wan-mode", mode], stderr=subprocess.STDOUT, timeout=15).decode()
                except Exception as e:
                    out = str(e)
            else:
                out = f"Invalid mode: '{mode}'. Allowed: 1, 2, 3"

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"output": out}).encode())
        else:
            self.send_response(404)
            self.end_headers()

with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
    httpd.serve_forever()
