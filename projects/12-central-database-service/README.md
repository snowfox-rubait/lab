# Project 12: Centralized Multi-Tenant Database Service (`db-central`)

> **Node:** Proxmox VE LXC 210 (`10.70.70.10`)  
> **Hypervisor Bridge:** Dedicated Database Tier (`vmbr7`)  
> **Base OS:** Debian GNU/Linux 13 (Trixie) - *Direct 1:1 Host Kernel & ABI Parity*  
> **Architectural Decisions:** [[../../knowledge/architecture-decisions#ADR-006 Dedicated Database Tier vmbr7 and Zero-Trust Inter-Bridge Firewall Hardening|ADR-006]] & [[../../knowledge/resource-planning-and-limits|Resource Planning]]

---

## 🎯 Architectural Role & Security Confinement

`db-central` consolidates database services for all homelab applications and cloud backups into a strictly isolated compute and network tier:

```
               [ OpenWrt VM (VM 100) Core Router ]
                                |
             +------------------+------------------+
             | Firewall Pinhole | Firewall Pinhole |
             v                  v                  v
     [ Safe Internal ]   [ Public Ingress ]  [ Unsafe / DMZ ]
          vmbr1               vmbr2            vmbr4 / vmbr5
    (Gitea, Immich, n8n)   (Vaultwarden)       (*Arr, Asterisk)
             |                  |                  |
       TCP: 5432, 6379       TCP: 5432             X
             |                  |            (HARD DROPPED)
             +--------+---------+
                      |
                      v
     +----------------------------------+
     |         vmbr7 (10.70.70.0/24)    |
     |  LXC 210: db-central (10.70.70.10)|
     |  - PostgreSQL 17.11 Multi-Tenant |
     |  - Redis 7 Session Store         |
     |  - Zero Outbound Internet Access |
     +----------------------------------+
```

### Key Security Standards:
1. **Zero Outbound Internet Access:** The database container has no WAN egress rule. Even in the event of an application SQL-injection or code exploit, automated payloads cannot call home or exfiltrate data.
2. **Dedicated Database Bridge (`vmbr7`):** Shares zero Layer-2 broadcast traffic with web applications, public tunnels, or IoT sensors.
3. **Host Version Parity (Debian 13 Trixie):** Matching the Proxmox host's base OS release eliminates cgroup/libc mismatches, minimizing namespace overhead and maximizing KSM memory deduplication.

---

## ⚙️ Multi-Tenant Architecture

Each connecting application is provisioned with an isolated role and database under `scram-sha-256` password hashing:

| Application | Target Database | Dedicated Role | Allowed Source IP | Allowed Ports |
| :--- | :--- | :--- | :--- | :--- |
| **Vaultwarden** | `vaultwarden_db` | `vaultwarden_user` | `10.20.20.11/32` (routed via `10.70.70.0/24`) | `TCP: 5432` |
| **Gitea** | `gitea_db` | `gitea_user` | `10.10.10.0/24` (`vmbr1`) | `TCP: 5432` |
| **n8n Automation** | `n8n_db` | `n8n_user` | `10.10.10.0/24` (`vmbr1`) | `TCP: 5432`, `TCP: 6379` |
| **Immich** | `immich_db` | `immich_user` | `10.10.10.0/24` (`vmbr1`) | `TCP: 5432`, `TCP: 6379` |
| **Neon Backup Sync**| `neon_backup_sync` | `backup_sync_bot` | `10.70.70.11/32` (`vmbr7`) | `TCP: 5432` |
| **Supabase Backup** | `supabase_backup` | `backup_sync_bot` | `10.70.70.11/32` (`vmbr7`) | `TCP: 5432` |

---

## 🛠️ Container Specifications

- **Container ID:** 210
- **Hostname:** `db-central`
- **vCPU:** 2 Cores (Fair-share CPU CFS scheduler)
- **RAM Assigned:** 2048 MB (Typical resident RAM ~400MB - 1GB)
- **Swap Assigned:** 1024 MB
- **Disk:** 15 GB on `local-lvm` thin pool
- **Network Interface:** `eth0` -> `vmbr7` (`10.70.70.10/24`, Gateway: `10.70.70.1`)

---

## 💾 Backup Data Flow & Cold Replication Architecture

To prevent architectural ambiguity regarding database backup direction and storage lifecycles:

```
[ db-central (LXC 210) ]
        │
   TCP: 5432 (PostgreSQL Read Stream via dedicated role 'backup_sync_bot')
        ▼
[ DBBackup Container (Planned LXC on vmbr7: 10.70.70.11) ]
        │
        ├── 1. Generate Local Dump: Automated 'pg_dump' across active tenant databases
        ├── 2. Local Encryption: GPG/Age encryption applied to snapshot artifacts
        ├── 3. Local Retention: Stored to local Proxmox backup storage (/backup/db)
        │
        ▼ (Outbound HTTPS / TLS via OpenWrt Firewall Pinhole strictly for Replication)
[ Remote Cloud Backup Endpoints (Supabase / Neon / Offsite S3) ]
```

### Key Principles:
1. **Query Direction vs. Storage Direction:** The backup daemon initiates an authenticated database read connection to PostgreSQL on `db-central`, generates compressed snapshot artifacts on local storage, and pushes encrypted backups to external cloud targets.
2. **Online Consistency:** Dumps run online using PostgreSQL multi-version concurrency control (MVCC) without requiring database downtime or cold stops.
3. **Restoration Drills:** Periodic disaster recovery verification takes place by importing test dumps into an isolated staging schema to verify schema and data integrity.
