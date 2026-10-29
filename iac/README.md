# 🤖 Infrastructure-as-Code (IaC) Automation Framework

> **Status:** Scaffolding & Initial Target Modules Active  
> **Philosophy:** Agentless, Minimal Overhead, Embedded-Friendly (OpenWrt & LXC Compatible)  
> **Standard:** `pyinfra` + Declarative POSIX Shell Playbooks  
> **Design Decision:** [ADR-007](../knowledge/architecture-decisions.md#adr-007-authoritative-internal-unicast-dns-lab-hierarchy-vs-multicast-dns-mdns-in-segmented-zero-trust-architecture) & Human Runbook Convergence

---

## 🎯 Purpose & Why `pyinfra` Over Ansible

In response to infrastructure audit feedback on idempotency and reproducibility:
- **The Ansible Problem on Embedded Routers:**  
  Standard Ansible requires a full Python runtime (`python3`, `python3-apt`) on all managed targets. The physical TP-Link Archer C6 v3 router has only **16MB SPI flash memory** with ~5.7MB free. Installing Python on OpenWrt would immediately exhaust flash storage and crash the overlay filesystem.
- **Why `pyinfra` Fits Our Homelab:**
  1. **Agentless & Zero Remote Dependencies:** Runs pure POSIX `/bin/sh` commands over SSH. Targets require only SSH access—zero Python required on the remote router or minimal Alpine/Debian containers.
  2. **Python-Native Playbooks:** Configuration logic is written in standard Python, allowing easy integration with `.env` secrets, dynamic IP lookups, and regex verification.
  3. **Blazing Speed:** Executes asynchronously over parallel SSH connections with instantaneous startup.
  4. **True Idempotency:** Detects existing file states, systemd services, and configuration hashes, mutating nodes only when configuration drift occurs.

---

## 🏗️ Directory Layout

```
iac/
├── README.md               # Architecture, tool comparison, and execution guide
├── inventory.py            # Target fleet inventory (.lab FQDNs, IPs, SSH aliases)
├── playbook.py             # Master fleet orchestration entrypoint
├── runner.sh               # Zero-dependency POSIX test & execution helper
└── tasks/
    ├── proxmox_host.py     # Proxmox VE host hardening (Fail2ban, Power Manager, KSM)
    ├── router_openwrt.py   # Physical Archer C6 OpenWrt (UCI network, strictorder, fw4)
    ├── wan_controller.py   # LXC 200 Out-of-Band WAN Controller (systemd, Python API, Nginx)
    └── pihole_oob.py       # LXC 205 DNS Sinkhole (.lab local records, gravity maintenance)
```

---

## 🚀 Quickstart & Execution

### 1. Installation (Management PC / Workstation)
Install `pyinfra` locally inside a virtualenv or via pip:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pyinfra
```

### 2. Fleet Dry-Run (Check Mode - Zero Changes)
To inspect what changes would be applied without modifying live systems:
```bash
pyinfra iac/inventory.py iac/playbook.py
```

### 3. Deploy Specific Subsystems
```bash
# Harden Proxmox Hypervisor Host:
pyinfra iac/inventory.py iac/tasks/proxmox_host.py

# Deploy WAN Controller WebUI (LXC 200):
pyinfra iac/inventory.py iac/tasks/wan_controller.py

# Configure Physical Router (UCI & wan-mode):
pyinfra iac/inventory.py iac/tasks/router_openwrt.py
```

### 4. Zero-Dependency POSIX Execution
For environments without `pyinfra` installed, `iac/runner.sh` provides standalone SSH connectivity verification and status checks:
```bash
./iac/runner.sh check
./iac/runner.sh status
```

---

## 🤝 Relationship with Markdown Runbooks

- **Playbooks (`iac/`) handle execution (the *WHAT*):** Automated package installation, service unit registration, file templating, and configuration verification.
- **Runbooks (`projects/XX-...`) document operations (the *WHY*):** Architecture context, manual failover verification drills, emergency recovery steps, and incident post-mortems.
- Both work together: runbooks link directly to corresponding playbooks for automated execution.
