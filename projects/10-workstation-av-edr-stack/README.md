# 🛡️ Project 10: Workstation Antivirus / EDR Stack & Incident Auto-Response

> **Project ID:** `10-workstation-av-edr-stack`  
> **Target Node:** Main PC Workstation (HP EliteDesk 800 G3 Mini, Arch Linux `rubait`)  
> **Status:** Planned / Architecture & Integration Blueprint  
> **Reference Specs:** [[../../linux_diy_security_stack|DIY Linux Security Stack — Feature Parity Map]] & [[../../av_tech_stack_breakdown|AV Tech Stack Breakdown]]  
> **Core Purpose:** Comprehensive host-based endpoint protection (YARA, ClamAV, osquery, Tetragon/eBPF, Falco) orchestrated via local Dockerized n8n and integrated into homelab incident-response cascades.

---

## 🎯 1. Overview & Objectives

The primary workstation runs a multi-layered open-source AV/EDR stack managed through Docker (`/home/test/Work/security-stack`), an in-house security dashboard (`security-dashboard` on port 8000), a local Ollama AI model (port 11434), and n8n (port 5678).

Instead of operating as an isolated silo, Project 10 integrates directly into the homelab's broader security automation:
1. **Host-Level Endpoint Protection:** Multi-engine static detection (ClamAV signatures, YARA rule matching), behavioral heuristics (eBPF process and network syscall monitoring), and file integrity auditing.
2. **AI-Assisted Alert Triage:** Local LLM triage (`security_alert_triage_n8n.json` via Ollama) classifying suspicious system events without sending telemetry to external clouds.
3. **Cross-Service Incident Cascade:** Triggering automated deep host scans whenever an external security breach is detected.

---

## ⚡ 2. The Breach Cascade: From Vaultwarden Leak to Workstation Antivirus Scan

### 2.1 The Threat Model & Rationale
When a password or credential breach is detected by **Project 08 (n8n)** via Have I Been Pwned:
- It indicates that account credentials were compromised either through a third-party server leak **or via local info-stealer malware** (e.g. RedLine, Lumma, Vidar, or browser session-hijacking scripts on the client PC).
- **Security Rule:** If an account credential is breached, the endpoint that generated or used that credential must be treated as potentially compromised until proven clean.

### 2.2 Cascading Automation Architecture

```
┌──────────────────────────────────────────────┐
│ Proxmox Hub / Project 08: n8n Watchdog       │
│ Checks HIBP via bw report password-health    │
└──────────────────────┬───────────────────────┘
                       │
                       ▼ (Breach Detected!)
       ┌───────────────┴───────────────┐
       │                               │
       ▼ (Outbound Alert)              ▼ (Mutual Ingress Webhook)
┌─────────────────────────────┐ ┌──────────────────────────────────────────┐
│ Project 09: Telegram Hub    │ │ Workstation: HP EliteDesk PC (rubait)    │
│ "Breach Alert: GitHub leaks │ │ POST https://pc.lan:5678/webhook/scan    │
│  Password updated in Vault! │ └────────────────────┬─────────────────────┘
│  Running Host Scan..."      │                      │
└─────────────────────────────┘                      ▼
                                ┌──────────────────────────────────────────┐
                                │ Project 10: Local Workstation AV Stack   │
                                ├──────────────────────────────────────────┤
                                │ 1. ClamAV: Full memory & browser scan    │
                                │ 2. YARA: Scan ~/.config/Brave*, /tmp     │
                                │ 3. osquery: Check anomalous crons/daemons│
                                │ 4. eBPF/Tetragon: Check active sockets   │
                                └────────────────────┬─────────────────────┘
                                                     │
                                                     ▼ (Scan Results & Telemetry)
                                ┌──────────────────────────────────────────┐
                                │ n8n Workflow: security_alert_triage      │
                                │ Triaged via Ollama Local LLM             │
                                └────────────────────┬─────────────────────┘
                                                     │
                                                     ▼ (Status Resolution)
                                ┌──────────────────────────────────────────┐
                                │ Project 09: Telegram Dispatcher          │
                                │ "Scan Clean: No active malware detected" │
                                │  or "ALERT: Suspicious artifact quarantined"
                                └──────────────────────────────────────────┘
```

---

## 🛠️ 3. Existing Local Workstation Assets & Tooling

The local PC already features pre-built infrastructure under `/home/test/Work/security-stack`:
- **Dockerized Services:**
  - `n8n` (`0.0.0.0:5678`): Host automation & triage executor.
  - `security-dashboard` (`0.0.0.0:8000`): Real-time web visualization for local detection events.
  - `ollama` (`0.0.0.0:11434`): Local AI inference model for alert analysis.
- **Workflow Catalog:**
  - `workflows/security_alert_triage_n8n.json`: Automated severity scoring and notification dispatch.
- **Scanning Scripts & Detection Hooks:**
  - `scripts/`: ClamAV scanning wrappers, YARA rule compilers, pacman pre-transaction validation hooks.

---

## 📋 4. Roadmap & Future Implementation

- [ ] **Phase 1: Webhook Ingress Authentication:** Configure a mutual HMAC-tokenized webhook in workstation n8n (`/webhook/av-incident-scan`) that accepts triggers strictly from trusted homelab management nodes (`192.168.1.2`, `10.10.10.0/24`).
- [ ] **Phase 2: Targeted Incident Scan Profile:** Create a high-priority, low-latency scan routine focused on info-stealer vectors:
  - Browser profile directories (`~/.config/BraveSoftware/`, `~/.mozilla/firefox/`).
  - Active persistence mechanisms (`~/.config/autostart/`, `systemctl --user list-timers`, `/etc/cron*`).
  - Ephemeral executable paths (`/tmp`, `/dev/shm`, `~/.local/bin`).
- [ ] **Phase 3: Automated Quarantine & Telegram Reporting:** If the cascade scan uncovers malicious binaries or suspicious persistence artifacts, quarantine the files and append diagnostic summaries to the ongoing Telegram breach incident card.
