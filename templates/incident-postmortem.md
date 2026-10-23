# 📋 Incident Postmortem Template

> **Purpose:** Blameless postmortem template to document outages, unexpected reboots, hardware hangs, security anomalies, and configuration failures across homelab nodes.

---

## 📌 Incident Summary

| Field | Details |
| :--- | :--- |
| **Incident Title** | [Brief descriptive summary of the incident] |
| **Date & Time (Detected)** | YYYY-MM-DD HH:MM (UTC+6) |
| **Date & Time (Resolved)** | YYYY-MM-DD HH:MM (UTC+6) |
| **Total Downtime** | [e.g. 15 minutes / 2 hours] |
| **Severity Level** | [P1 - Critical Outage / P2 - Major Degradation / P3 - Minor Glitch] |
| **Impacted Nodes / Zones** | [e.g. Physical Router, OpenWrt VM, vmbr1, Home Wi-Fi] |
| **Lead Responder** | [e.g. Rubait] |

---

## 💥 Impact Description
- **User Impact:** What did users (or home devices) experience? (e.g. Wi-Fi drop, password vault unreachable).
- **Service Impact:** Which services, containers, or network bridges failed or hung?

---

## ⏱️ Incident Timeline
*Record key events in chronological order (UTC+6)*

- **HH:MM** - Anomaly occurred / triggered.
- **HH:MM** - Incident detected via [alerts / manual observation / ping failure].
- **HH:MM** - Initial triage commenced; hypothesis formed.
- **HH:MM** - Mitigation step 1 executed [e.g. reboot / route switch].
- **HH:MM** - Root cause isolated.
- **HH:MM** - Full service restored & verified.

---

## 🔍 Root Cause Analysis (5 Whys)
1. **Why did the outage happen?**
   - ...
2. **Why?**
   - ...
3. **Why?**
   - ...
4. **Why?**
   - ...
5. **Why?**
   - ...

---

## 🛠️ Resolution & Recovery
- What immediate actions were taken to restore service?
- Were there any workarounds applied that need cleanup?

---

## 🧠 Lessons Learned & Action Items

### What went well:
- ...

### What could be improved:
- ...

### Preventative Action Items:
- [ ] **Action 1:** [Owner: Rubait] - [Preventative fix / monitoring addition]
- [ ] **Action 2:** [Owner: Rubait] - [Documentation or script update]
