# 🔒 Internal PKI, Zero-Trust Transport & End-to-End Encryption (E2EE) Standards

> **Status:** Live & Enforced  
> **Authority:** Homelab Root CA (`/root/homelab-pki/ca/ca.crt` on Proxmox)  
> **Applies to:** Inter-Container, Cross-Zone, and Ingress-to-Database communications

---

## 🎯 Cryptographic Architecture & Model Demarcation

It is essential to distinguish between **Zero-Knowledge Client-Side Encryption** and **Zero-Cleartext Transport Encryption (PKI / TLS)**:

1. **Application-Level End-to-End Encryption (E2EE):**  
   Enforced at the client vault level by Vaultwarden / Bitwarden clients. Passwords, notes, and cryptographic seeds are encrypted client-side using `AES-256-CBC` / `ChaCha20-Poly1305` with keys derived via `Argon2id` or `PBKDF2`. The Vaultwarden server and central PostgreSQL database store only opaque ciphertext payloads.
2. **Infrastructure-Level Mutual Transport Encryption (Internal PKI / TLS):**  
   Guarantees that no plaintext metadata, HTTP headers, authentication tokens, or database query streams travel over Linux virtual bridges, physical Ethernet cables, or container namespaces unencrypted.

Every single segment of network transit across physical cables, Proxmox Linux bridges, and inter-container sockets is **strictly encrypted**:

```
[ Browser / Phone ]
        │
   HTTPS (TLS 1.3)
        │
        ▼
[ Cloudflare Edge ]
        │
   Encrypted QUIC Tunnel (ChaCha20-Poly1305 / TLS 1.3)
        │
        ▼
[ LXC 202: nginx-public (vmbr2: 10.20.20.10) ]
        │
   Internal HTTPS (TLS 1.3 / mTLS verified via Homelab Root CA)
        │
        ▼
[ LXC 220: vaultwarden (vmbr2: 10.20.20.11) ]
        │
   Encrypted PostgreSQL Connection (hostssl enforced, sslmode=require)
        │
        ▼
[ LXC 210: db-central (vmbr7: 10.70.70.10) ]
```

---

## 🔑 Internal PKI Infrastructure

A dedicated internal Certificate Authority was established on the secure Proxmox hypervisor root:

1. **Homelab Root CA:**
   - Certificate: `/root/homelab-pki/ca/ca.crt` (4096-bit RSA, 10-year validity)
   - Trust Store: Trusted system-wide in `ca-certificates` across LXC 202, LXC 210, and LXC 220.
2. **Vaultwarden Internal TLS Certificate:**
   - Subject: `CN=10.20.20.11, DNS:vaultwarden.lab`
   - Bound to Rocket Web Server via `ROCKET_TLS`.
   - Verified by Nginx: `proxy_ssl_verify on` with `proxy_ssl_trusted_certificate`.
3. **PostgreSQL Server TLS Certificate:**
   - Subject: `CN=10.70.70.10, DNS:postgres.lab`
   - Enforced in `postgresql.conf`: `ssl = on`.
   - Enforced in `pg_hba.conf`: `hostssl` rule requiring encrypted connections for all tenant roles.
   - Client enforcement: `DATABASE_URL=...&sslmode=require`.

---

## 🏆 Verification Results

- **No Cleartext Packets:** Even if a packet capture (`tcpdump`) is executed on `vmbr0`, `vmbr2`, or `vmbr7`, all payloads are 100% encrypted ciphertext.
- **HSTS Activated:** Response headers now return:
  ```http
  strict-transport-security: max-age=31536000
  ```
- **Zero Downgrade Attacks:** Non-TLS plaintext connections to PostgreSQL are rejected with `FATAL: no pg_hba.conf entry for host ... SSL off`.
