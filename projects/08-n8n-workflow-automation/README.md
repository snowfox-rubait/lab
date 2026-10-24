# 🔄 Project 08: n8n Workflow Automation Hub

> **Project ID:** `08-n8n-workflow-automation`  
> **Target Subnet:** Safe Offline Bridge (`vmbr1`, `10.10.10.0/24`) or Safe Public Ingress (`vmbr2`, `10.20.20.0/24`)  
> **Status:** Planned / Architecture & Security Blueprint  
> **Core Purpose:** Centralized self-hosted low-code workflow automation orchestrating homelab services, scheduled telemetry, security notifications, and incident response pipelines.

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

- **Network Zone:** Placed inside **Safe Offline Bridge (`vmbr1`)** with granular egress routing to `vmbr2` (Vaultwarden) and internet access via physical router gateway (`192.168.1.1`) for external APIs (Telegram, HIBP).
- **Database Dependency:** Centralized PostgreSQL backend on Dedicated Database Tier (`vmbr7`, `10.70.70.10:5432`).
- **Security Ingress:** Accessible internally at `n8n.snowfox.live` via `nginx-safe` reverse proxy; public webhook triggers authenticated via HMAC signatures.

---

## 🛡️ 3. Featured Pipeline: Vaultwarden Breach Monitor & Auto-Remediation

### 3.1 The Concept
An autonomous security watchdog that:
1. Audits stored credentials against the **Have I Been Pwned (HIBP)** breach database every 10 minutes.
2. Immediately alerts the administrator via **Telegram** when a breach or compromised credential is detected.
3. Automatically rotates and updates the compromised credential with a cryptographically strong newly generated passphrase in Vaultwarden.
4. Preserves the prior password in Vaultwarden's native password history so the user can authenticate into the affected service.
5. Sends an interactive Telegram message containing:
   - Name of the compromised account and username/email.
   - Direct recovery URL (resolving standard `/.well-known/change-password` or stored login URI).
   - Guidance requiring manual rotation of non-automatable factors (Passkeys/FIDO2, TOTP authenticator keys).
6. **Cascades Workstation Malware Inspection (Project 10):** Dispatches a webhook to the Main PC's local security stack (`projects/10-workstation-av-edr-stack`) to trigger an immediate background ClamAV/YARA memory and browser-storage audit to verify that the breach did not originate from a local info-stealer Trojan.

### 3.2 Technical Feasibility Analysis

| Automation Step | Feasibility | Technical Mechanism |
| :--- | :--- | :--- |
| **Periodic Breach Check** | ✅ **100% Feasible** | Runs `bw report password-health` via Bitwarden CLI or calls HIBP API directly using $k$-anonymity SHA-1 prefixes. |
| **Instant Telegram Alert** | ✅ **100% Feasible** | Uses n8n Telegram Node with inline keyboard action buttons for recovery links. |
| **Auto-Generate New Password** | ✅ **100% Feasible** | `bw generate --passphrase --words 5 --separator "-"` or built-in n8n Crypto module. |
| **Update Vault Record & Save** | ✅ **100% Feasible** | `bw get item <id>` ➔ update `.login.password` ➔ `bw encode` ➔ `bw edit item <id>`. |
| **Preserve Password History** | ✅ **Native Bitwarden Feature** | When a password field is overwritten via `bw edit item`, Vaultwarden automatically appends the previous password to `.passwordHistory` with timestamps. |
| **Change Password URL Extraction** | ✅ **100% Feasible** | Bitwarden Login items store `uri`. The pipeline extracts the domain and appends standard `/.well-known/change-password` (W3C standard), falling back to the login URI. |
| **Automated Passkey/TOTP Rotation** | ⚠️ **Intentionally Manual** | Cryptographic design of WebAuthn/FIDO2 passkeys requires local hardware-bound public-key registration in the user's browser; cannot be blindly rotated without interactive browser session. |

### 3.3 n8n Workflow Architecture

```
[ Cron Trigger: Every 10 min ]
               │
               ▼
[ Bitwarden CLI / Vault Health Audit ]
  Command: bw report password-health
               │
               ▼
[ Filter: exposedCount > 0 && !tag.includes('acknowledged') ]
               │
               ├── (Breach Detected)
               ▼
[ 1. Generate High-Entropy Passphrase ]
  (e.g., 5-word random passphrase)
               │
               ▼
[ 2. Update Vaultwarden Item via CLI ]
  Overwrites item password (pushes old to history)
               │
               ▼
[ 3. Construct Recovery URL ]
  Resolves https://<domain>/.well-known/change-password
               │
               ▼
[ 4. Dispatch Interactive Telegram Alert ]
  Sends markdown card + direct "Open Change Password Page" button
```

---

## 📋 4. Roadmap & Planned Future Implementations

- [ ] **Phase 1: n8n Container Deployment:** Provision Proxmox Debian LXC with rootless containerized n8n on `vmbr1` (`10.10.10.25`).
- [ ] **Phase 2: Database Centralization:** Connect n8n state storage to PostgreSQL on `vmbr7` (`10.70.70.10:5432`).
- [ ] **Phase 3: Vaultwarden Watchdog Node:** Build the Bitwarden CLI sidecar and test `bw report password-health` in sandbox.
- [ ] **Phase 4: Multi-Service Alert Dispatcher:** Integrate Proxmox backup notifications, OpenWrt WAN status changes, and Pi-hole DNS sinkhole statistics into unified n8n workflows.
