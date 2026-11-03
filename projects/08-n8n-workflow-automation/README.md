# 🔄 Project 08: n8n Workflow Automation Hub

> **Project ID:** `08-n8n-workflow-automation`  
> **Node:** Proxmox VE LXC 240 (`10.10.10.25`)  
> **Target Subnet:** Safe Internal Zone (`vmbr1`, `10.10.10.0/24`)  
> **Status:** 🟢 Live & Production Verified  
> **Infrastructure as Code:** Declarative Terraform (`iac/terraform/proxmox/lxc-n8n.tf`)  
> **Core Purpose:** Centralized self-hosted workflow automation orchestrating homelab services, scheduled telemetry, security notifications, and incident response pipelines.

---

## 🎯 1. Overview & Objectives

n8n serves as the homelab's central automation engine. Instead of scattering hardcoded cron scripts across multiple virtual machines and containers, n8n provides:
1. **Visual Pipeline Orchestration:** Node-based workflow management with native retry policies, error triggers, and webhooks.
2. **Encrypted Credential Storage:** API tokens, SSH keys, Telegram bot secrets, and database credentials stored encrypted at rest.
3. **Cross-Service Automation:** Bridging events between Proxmox VE, OpenWrt, Vaultwarden, Pi-hole, Gitea, and Telegram.
4. **Autonomous Security Auditing:** Periodic breach detection, backup integrity checks, and proactive system health alerts.

---

## 🏗️ 2. Architectural Placement & Network Boundaries

```
[ Homelab Network Topology ]
                       │
                       ▼
       ┌───────────────────────────────┐
       │   Proxmox VE Hypervisor       │
       │                               │
       │   [CT: n8n Automation Engine] │
       │   IP: 10.10.10.25 (vmbr1)     │
       │                               │
       └───┬───────────────────────┬───┘
           │                       │
           │ (Internal API/RPC)    │ (HTTPS Webhook / REST)
           ▼                       ▼
┌──────────────────────┐ ┌───────────────────────────┐
│ Vaultwarden Backend  │ │ Telegram Bot Hub          │
│ IP: 10.20.20.11      │ │ Project 09 (Telegram API) │
│ (bw CLI / Vault API) │ │ Incident Dispatch         │
└──────────────────────┘ └───────────────────────────┘
```

- **Network Zone:** Placed inside **Safe Internal Zone (`vmbr1`, `10.10.10.0/24`)** with default gateway `10.10.10.1` (OpenWrt VM), with granular firewall pinholes to `vmbr2` (`10.20.20.11:8443` Vaultwarden) and `vmbr7` (`10.70.70.10:5432` PostgreSQL). Outbound internet access routes through OpenWrt VM NAT for external APIs (Telegram, HIBP).
- **Database Dependency:** Centralized PostgreSQL backend on Dedicated Database Tier (`vmbr7`, `10.70.70.10:5432`).
- **Security Ingress:** Accessible internally at `n8n.snowfox.live` via `nginx-safe` reverse proxy; public webhook triggers authenticated via HMAC signatures.

---

## 🛡️ 3. Featured Pipeline: Vaultwarden Breach Monitor, Alert & Assisted Triage Flow

### 3.1 The Concept & Safety Boundaries
An autonomous security watchdog designed to detect credential compromise and assist immediate human remediation:
1. **Periodic Exposure Audit:** Audits stored credentials against the **Have I Been Pwned (HIBP)** breach database using $k$-anonymity SHA-1 hash prefixes (zero plaintext passwords sent to external APIs).
2. **Instant High-Priority Alert:** When a compromised password is confirmed, n8n immediately dispatches an urgent incident alert via **Telegram Bot Hub** (`projects/09-telegram-bot-hub`).
3. **Suggested Strong Passphrase Generation:** n8n pre-generates a cryptographically strong, high-entropy 5-word passphrase suggestion and includes it directly in the incident card.
4. **Direct Change-Password Link:** Resolves W3C standard `/.well-known/change-password` from the vault item's URI so the administrator can jump directly to the remote provider's reset page.
5. **No Blind Vault Overwriting (Human-Verified Rotation):**
   > [!CRITICAL]
   > **Why Blind Auto-Overwriting Vaultwarden is Unsafe:**  
   > Changing a password inside a local Vaultwarden database does *not* rotate the password at the remote service (e.g. Google, GitHub, banks). Overwriting the stored password automatically would lock the user out of the remote service while leaving the breached password active on the remote endpoint.  
   > Therefore, Vaultwarden records are updated **only after** the administrator completes the remote password change, or via two-stage confirmation.
6. **Workstation Malware Cascade (Project 10):** Dispatches an authenticated webhook to the Main PC's endpoint defense stack (`projects/10-workstation-av-edr-stack`) to trigger an immediate background ClamAV/YARA memory and browser-storage audit to verify that the breach did not originate from a local info-stealer Trojan.

### 3.2 Technical Feasibility Analysis

| Automation Step | Feasibility | Technical Mechanism |
| :--- | :--- | :--- |
| **Periodic Breach Check** | ✅ **100% Feasible** | Queries HIBP API via $k$-anonymity (first 5 chars of SHA-1 hash) or uses Bitwarden CLI vault exports. |
| **Instant Telegram Alert** | ✅ **100% Feasible** | Uses n8n Telegram Node with inline keyboard action buttons for recovery links. |
| **Pre-Generate Replacement Passphrase** | ✅ **100% Feasible** | Built-in n8n Crypto module generates high-entropy 5-word Diceware passphrase. |
| **Change Password URL Extraction** | ✅ **100% Feasible** | Parses domain from item URI and appends standard `/.well-known/change-password` (W3C standard), falling back to root login URL. |
| **Remote Service Password Rotation** | ⚠️ **Human / Service API Bound** | Executed by user via direct link, or via dedicated provider APIs where supported. |
| **Post-Verification Vault Update** | ✅ **100% Feasible** | Upon user confirmation callback, `bw edit item <id>` updates vault, natively preserving old password in `.passwordHistory`. |
| **Automated Passkey/TOTP Rotation** | ⚠️ **Intentionally Manual** | Cryptographic design of WebAuthn/FIDO2 passkeys requires local hardware-bound public-key registration in the user's browser. |

### 3.3 n8n Workflow Architecture

```
[ Cron Trigger: Every 15 min ]
               │
               ▼
[ HIBP k-Anonymity Hash Audit ]
  Queries range API (5-char SHA-1 prefix)
               │
               ▼
[ Filter: exposedCount > 0 && !acknowledged ]
               │
               ├── (Breach Confirmed)
               ▼
[ 1. Generate High-Entropy Suggested Passphrase ]
  (Cryptographically secure 5-word Diceware passphrase)
               │
               ▼
[ 2. Construct Direct Reset URL ]
  Resolves https://<domain>/.well-known/change-password
               │
               ▼
[ 3. Dispatch Interactive Telegram Alert ]
  Sends incident card with:
  - Account name & username
  - Direct "Change Password" button
  - Copyable suggested replacement passphrase
  - Interactive callback [ ✅ Mark Rotated & Update Vault ]
               │
               ▼ (Cascade Trigger)
[ 4. Dispatch Webhook to Workstation EDR (Project 10) ]
  Triggers host info-stealer scan on Admin Workstation
```

---

## 📋 4. Roadmap & Implementation Status

- [x] **Phase 1: n8n LXC Container Deployment:** Provisioned Proxmox Debian 13 LXC 240 with native Node.js 22 LTS on `vmbr1` (`10.10.10.25`), managed via `systemd` (`n8n.service`).
- [x] **Phase 2: Database Centralization:** Connected n8n state storage to PostgreSQL 17 on `db-central` (`vmbr7`, `10.70.70.10:5432`, `n8n_db`).
- [x] **Phase 3: Ingress & Split-Horizon TLS:** Routed through `nginx-safe` (`10.10.10.10`) on `https://n8n.snowfox.live` with WebSocket support.
- [x] **Phase 4: Declarative Infrastructure:** Fully managed via Terraform (`iac/terraform/proxmox/lxc-n8n.tf`).
- [ ] **Phase 5: Vaultwarden Watchdog Node:** Build the Bitwarden CLI sidecar and test `bw report password-health` in sandbox.
- [ ] **Phase 6: Multi-Service Alert Dispatcher:** Integrate Proxmox backup notifications, OpenWrt WAN status changes, and Pi-hole DNS sinkhole statistics into unified n8n workflows.

---

## 🛠️ 5. Production Specifications & Service Units

### 5.1 Environment Configuration (`/etc/n8n/n8n.env`)
```env
# Server Network Settings
N8N_HOST=0.0.0.0
N8N_PORT=5678
N8N_PROTOCOL=https
WEBHOOK_URL=https://n8n.snowfox.live/
GENERIC_TIMEZONE=Asia/Dhaka

# PostgreSQL Database Backend (LXC 210 db-central)
DB_TYPE=postgresdb
DB_POSTGRESDB_HOST=10.70.70.10
DB_POSTGRESDB_PORT=5432
DB_POSTGRESDB_DATABASE=n8n_db
DB_POSTGRESDB_USER=n8n_user
DB_POSTGRESDB_PASSWORD=<SCRUBBED_POSTGRES_PASS>
DB_POSTGRESDB_SSL=true
DB_POSTGRESDB_SSL_REJECT_UNAUTHORIZED=false

# Storage & Confinement
N8N_USER_FOLDER=/var/lib/n8n
N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=true
N8N_LOG_LEVEL=info
N8N_LOG_OUTPUT=console,file
N8N_LOG_FILE_LOCATION=/var/lib/n8n/n8n.log
N8N_LOG_FILE_MAX_SIZE=10
N8N_LOG_FILE_MAX_COUNT=5
```

### 5.2 Systemd Unit (`/etc/systemd/system/n8n.service`)
```ini
[Unit]
Description=n8n Workflow Automation Hub
After=network.target

[Service]
Type=simple
User=n8n
Group=n8n
EnvironmentFile=/etc/n8n/n8n.env
ExecStart=/usr/bin/n8n
Restart=always
RestartSec=10
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

---

## 🔬 6. Engineering Post-Mortem: What, How, Why, Failures & Solves

### A. The "What, How, and Why" Summary
- **What:** Provisioned n8n inside Proxmox LXC 240 running natively on Node.js 22 LTS with state persisted directly to PostgreSQL 17 on `db-central` (`10.70.70.10`), reverse-proxied via `nginx-safe` on `https://n8n.snowfox.live`.
- **How:** Deployed unprivileged Debian 13 LXC on `vmbr1`, configured NodeSource Node.js 22 LTS repos, created PostgreSQL user and schema on LXC 210, deployed systemd service unit, enabled WebSocket upgrade in Nginx, and imported the resource into Terraform.
- **Why:** Avoids nested Docker overhead, saves ~200 MB of resident RAM, guarantees persistent workflow execution state in central encrypted database backups, and keeps ingress strictly non-public via Split-Horizon DNS and Tailscale.

### B. Failures Encountered & Engineering Solutions

#### 1. Failure: Node.js 20 Engine Rejections (`EBADENGINE`) & Platform Mismatches (`EBADPLATFORM`)
- **Symptoms:** Running `npm install -g n8n` on Debian 13's native Node.js 20.19.2 failed with fatal errors:
  ```
  npm ERR! code EBADENGINE (required: { node: '>=22' })
  npm ERR! notsup Unsupported platform for @napi-rs/canvas-linux-arm64-musl: wanted {"os":"linux","arch":"arm64"}
  ```
- **Root Cause:** Modern n8n packages (LangChain, Azure SDK, Vue 3.5, OpenTelemetry) mandate Node.js >= 22.x, and npm 9 evaluated optional platform binaries strictly.
- **Engineering Solution:** Deployed the official NodeSource Node.js 22.x LTS repository (`curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && apt-get install -y nodejs`), which upgraded the runtime to Node `v22.23.4` and npm `10.9.9`. Installed with `--legacy-peer-deps` to smoothly resolve the 2,017-package tree.

#### 2. Failure: PostgreSQL Multi-Statement Transaction Error
- **Symptoms:** Creating database and user in a single `psql -c` command aborted:
  `ERROR: CREATE DATABASE cannot run inside a transaction block`.
- **Root Cause:** PostgreSQL executes multiple statements passed to `-c` inside an implicit transaction (`BEGIN ... COMMIT`). `CREATE DATABASE` cannot execute within an active transaction.
- **Engineering Solution:** Executed separate atomic `psql -c` statements for `CREATE ROLE`, `CREATE DATABASE`, and `GRANT ALL PRIVILEGES`.

#### 3. Failure: Interrupted `npm install` on In-Place Metadata Updates
- **Symptoms:** During initial npm package compilation, the process exited with code `143` (SIGTERM).
- **Root Cause:** Running an uncoordinated Terraform state sync during active package installation signaled the container.
- **Engineering Solution:** Completed Terraform import with protective lifecycle blocks first, then re-ran `npm install -g --legacy-peer-deps n8n`. Because npm already cached downloaded packages in `/root/.npm`, the subsequent run finished cleanly and linked `/usr/bin/n8n`.

