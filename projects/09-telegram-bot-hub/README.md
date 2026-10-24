# 🤖 Project 09: Centralized Telegram Bot & Alerting Hub

> **Project ID:** `09-telegram-bot-hub`  
> **Target Subnet:** Safe Internal Zone (`vmbr1`, `10.10.10.0/24`) or Management Bots Zone (`vmbr6`, `10.60.60.0/24`)  
> **Status:** Planned / Architecture & Security Blueprint  
> **Core Purpose:** The central interactive notification, operations, and alerting clearinghouse for all homelab services, hypervisors, network appliances, and automation pipelines.

---

## 🎯 1. Overview & Objectives

While **Project 06** (`06-openwrt-telegram-bot`) is dedicated specifically to out-of-home router controls (Wi-Fi, port toggling, guest networks, wan-mode), **Project 09** acts as the umbrella **Homelab Bot Hub & Dispatcher** for all other services:

1. **Centralized Incident Dispatch:** One authoritative bot token and chat thread for high-priority homelab alerts (server outages, disk failures, security breaches).
2. **Interactive Remediations:** Rich inline buttons (e.g. `[Acknowledge]`, `[Open Password Reset]`, `[Restart Container]`, `[Extend Guest Wi-Fi]`).
3. **Multi-Service Alert Aggregation:**
   - **n8n Automation (Project 08):** Vaultwarden breach alerts, automated report summaries.
   - **Proxmox VE (Project 00):** Backup completion, smartd disk degradation, snapshot alerts.
   - **Pi-hole (Project 07):** Sudden DNS query spikes, high adblock rate anomalies.
   - **Gitea / CI:** Commit webhooks, backup job logs.
4. **Security Isolation:** Strict sender authorization using Telegram `ChatID` whitelisting to prevent unauthorized access.

---

## 🏗️ 2. Architectural Relationship with Other Projects

```
                      ┌──────────────────────────────────────┐
                      │            Telegram Cloud            │
                      └──────────────────┬───────────────────┘
                                         │
                                         ▼ (Encrypted Bot API)
                      ┌──────────────────────────────────────┐
                      │ Project 09: Telegram Bot Hub         │
                      │ Dispatcher, Router & Auth Layer      │
                      └──────────────────▲───────────────────┘
                                         │
       ┌───────────────────┬─────────────┴───────┬───────────────────┐
       │                   │                     │                   │
┌──────┴──────────┐ ┌──────┴──────────┐   ┌──────┴──────────┐ ┌──────┴──────────┐
│ Project 08: n8n │ │ Project 00: PVE │   │ Project 07:     │ │ Project 03:     │
│ Breach Watchdog │ │ Hypervisor Host │   │ Pi-hole DNS     │ │ Vaultwarden     │
│ & Automations   │ │ Backups / SMART │   │ Spikes / Drops  │ │ Security Audit  │
└─────────────────┘ └─────────────────┘   └─────────────────┘ └─────────────────┘
```

---

## 🔔 3. Breach Alert Message Specification (n8n & Vaultwarden Integration)

When a breach is detected by Project 08, Project 09 formats and dispatches the incident notification card:

```markdown
🚨 *SECURITY ALERT: Compromised Credential Detected!*

*Affected Service:* GitHub
*Username / Email:* test@snowfox.live
*Breach Source:* Known Data Breach (Have I Been Pwned)
*Times Seen in Breaches:* 4 times
*Action Taken:* 
- ✅ Generated new high-entropy passphrase in Vaultwarden.
- 🔒 Prior password saved to historical revisions.

⚠️ *Immediate Action Required:*
1. Log in to the service using your old password (stored in history).
2. Update the service to use the newly generated password.
3. Review and cycle any active Passkeys, WebAuthn keys, or 2FA TOTP seeds.

[🔗 Open Change Password Page](https://github.com/.well-known/change-password)
[🛡️ View Item in Vaultwarden](https://vault.snowfox.live/#/vault?itemId=...)
```

---

## 📋 4. Roadmap & Future Capabilities

- [ ] **Phase 1: Bot Token & Chat Registry:** Register bot via `@BotFather`, securely store API credentials in gitignored `.env` and n8n credentials vault.
- [ ] **Phase 2: Alert Dispatch Webhook:** Create standardized HTTP REST webhook (`POST /api/notify`) in n8n for lightweight curl notifications from any homelab script.
- [ ] **Phase 3: Interactive Command Callbacks:** Implement Telegram interactive callback handlers for homelab state queries (`/pve status`, `/pihole stats`, `/breach status`).
- [ ] **Phase 4: Multi-Channel Escalation:** Add fallback alerting channels (e.g., Pushover or Gotify) in case Telegram API is unreachable or rate-limited.
