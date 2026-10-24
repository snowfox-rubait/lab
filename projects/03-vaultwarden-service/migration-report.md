# 🏆 Vaultwarden Production Migration Report: SQLite to PostgreSQL 17

> **Date Completed:** 2026-10-24  
> **Source System:** Workstation Docker SQLite (`/home/test/vaultwarden/data/db.sqlite3`)  
> **Target Production System:** Proxmox LXC 220 (`vaultwarden` on `vmbr2`) + LXC 210 (`db-central` on `vmbr7`)  
> **Ingress Gateway:** LXC 202 (`nginx-public` on `vmbr2` with `cloudflared`)  
> **Status:** 🟢 **100% SUCCEEDED & VERIFIED LIVE**

---

## 📊 Data Verification & Integrity Audit

All existing accounts, credentials, and cryptographic parameters were cleanly transformed with boolean type-casting and schema alignment into the production PostgreSQL cluster:

| Dataset / Table | Source (SQLite) | Target (`vaultwarden_db` PostgreSQL 17) | Verification Status |
| :--- | :---: | :---: | :---: |
| **Registered Users (`users`)** | 2 | 2 | ✅ Verified 1:1 Match |
| **Encrypted Ciphers (`ciphers`)** | 127 | 127 | ✅ Verified 1:1 Match |
| **Authorized Devices (`devices`)** | 18 | 18 | ✅ Verified 1:1 Match |
| **Instance Keypair (`rsa_key.pem`)**| SHA256 preserved | Deployed to `/vw-data/rsa_key.pem` | ✅ Verified 1:1 Match |

---

## 🏗️ Live End-to-End Topology & Data Flow

```
                      [ Cloudflare Edge / WAF ]
                                  │
                   (Encrypted Cloudflare Tunnel)
                                  │
                                  ▼
           [ LXC 202: nginx-public (10.20.20.10 on vmbr2) ]
              ├── cloudflared daemon (Ingress termination)
              └── Nginx Reverse Proxy (:80)
                    ├── /admin: 403 Forbidden (Blocked for external)
                    ├── /notifications/hub: WebSocket Proxy (:3012)
                    └── /: Application Proxy (:8085)
                                  │
                                  ▼
           [ LXC 220: vaultwarden (10.20.20.11 on vmbr2) ]
              └── Vaultwarden Engine (Rocket :8085)
                                  │
                    (OpenWrt Firewall Pinhole: TCP:5432)
                                  │
                                  ▼
           [ LXC 210: db-central (10.70.70.10 on vmbr7) ]
              └── PostgreSQL 17 Multi-Tenant (vaultwarden_db)
```

---

## 🔒 Security Hardening Implemented

1. **Dedicated Database Tier (`vmbr7`):** The PostgreSQL database resides in an offline bridge with zero WAN internet access and strict firewall pinhole allowance (`10.20.20.11:5432`).
2. **Admin Panel Confinement:** Access to `/admin` returns `403 Forbidden` through the public ingress proxy; reachable only via local admin PC (`192.168.1.197`).
3. **Session & Token Continuity:** By transferring `rsa_key.pem` directly from your workstation to LXC 220, all active browser extensions, mobile apps, and device login tokens remain valid without requiring master password re-authentication.
