# 📊 Hypervisor Sizing, Resource Planning & Virtualization Constraints

> **Hardware Node:** ThinkPad T430 / L430 (`192.168.1.2`)  
> **Host OS:** Proxmox VE 9.2.2 on **Debian 13 (Trixie)** (Kernel 7.0.2-6-pve)  
> **Compute Specs:** Intel(R) Core(TM) i5-3210M @ 2.50GHz (2 Cores, 4 Threads)  
> **Memory Specs:** 8 GB DDR3 RAM (`7.6 GiB` visible), 4 GB Swap (`sda3`)  
> **Storage Specs:** 120 GB SSD (`local-lvm` thin pool: 52.3 GB)

---

## 🎯 Golden Standards & Architectural Constraints

### 1. Host OS Matching Preference (Debian 13 Trixie)
- **Standard:** Whenever provisioning Linux Containers (LXC), prefer templates matching the Proxmox Host's base Debian release (**Debian 13 Trixie** via `debian-13-standard_13.6-1_amd64.tar.zst`).
- **Benefits:**
  - Identical libc, systemd, and kernel ABI expectations between host and container namespaces.
  - Zero translation overhead for shared kernel cgroups v2.
  - Up-to-date PostgreSQL 17 and modern package repos without backports.

---

## 🧠 Memory Sharing Concepts: "Bloating" vs "Ballooning" vs "KSM"

The term commonly heard as *"bloating"* is actually one of two hypervisor technologies in Proxmox:

### A. Memory Ballooning (`virtio-balloon` - VMs only)
- **What it is:** A kernel driver inside KVM virtual machines (like OpenWrt VM 100) that inflates or deflates a virtual "balloon" inside the guest OS.
- **How it helps:** If a VM is allocated 2GB of RAM but only uses 300MB, Proxmox dynamically inflates the balloon, claiming the remaining 1.7GB back for the host and other containers to use.
- **Applicability:** Critical for VMs. *Note: LXC containers don't even need ballooning because LXCs are native Linux cgroups—they only consume the exact resident RAM their processes actually use!*

### B. Kernel Samepage Merging (KSM - RAM Deduplication)
- **What it is:** A Linux kernel daemon (`ksmd`) that scans physical RAM for identical memory pages across different containers/VMs (e.g. identical Debian 13 shared libraries, bash binaries, libc) and merges them into a single read-only physical page with Copy-On-Write (COW).
- **How it helps:** When running multiple Debian 13 containers, KSM can save **20% to 35% of total RAM**, effectively turning 8GB of physical RAM into the equivalent of 10-11GB.
- **Status:** Currently idle (`0`). Can be enabled via `/etc/ksmtuned.conf` once multiple LXCs are deployed.

### C. CPU Overcommit (Fair-Share Scheduling)
- KVM VMs and LXC containers share physical CPU threads via the Linux Completely Fair Scheduler (CFS).
- **Core Allocation Rule:** Giving 2 vCPUs to 5 different containers does **NOT** require 10 physical cores. Idle containers consume **0.1% CPU**. The CPU is dynamically time-sliced when requests arrive (e.g. database query, password hash).

---

## 📈 Capacity Planning & Budget Matrix (8 GB RAM / 4 Threads)

Here is the exact capacity breakdown for your intended homelab suite:

| Service / Workload | Type | vCPU Allocation | RAM Assigned | Actual Resident RAM | Proxmox Bridge |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **PVE Hypervisor Host** | Host | 4 Threads | Base Reserve | ~1.2 GiB | - |
| **OpenWrt VM (VM 100)** | KVM | 1 vCPU | 512 MiB | ~180 MiB | `vmbr0`..`vmbr7` |
| **WAN Controller (LXC 200)** | LXC | 1 vCPU | 512 MiB | ~65 MiB | `vmbr0` |
| **Pi-hole OOB (LXC 205)** | LXC | 1 vCPU | 512 MiB | ~95 MiB | `vmbr0` |
| **Central Database (LXC 210)**| LXC | 2 vCPU | 2048 MiB | ~400 MiB - 1 GiB | `vmbr7` |
| **Vaultwarden (LXC 220)** | LXC | 1 vCPU | 512 MiB | ~80 MiB | `vmbr2` |
| **Headscale (Deferred)** | LXC | 1 vCPU | 512 MiB | ~60 MiB | Undecided / Separated |
| **n8n Automation (LXC 240)** | LXC | 1 vCPU | 1024 MiB | ~350 MiB | `vmbr1` |
| **Telegram Hub (LXC 250)** | LXC | 1 vCPU | 512 MiB | ~70 MiB | `vmbr0` / `vmbr1` |
| **Gitea + Actions (LXC 260)** | LXC | 1 vCPU | 1024 MiB | ~250 MiB | `vmbr1` |
| **Kiwix / ZIM (LXC 270)** | LXC | 1 vCPU | 512 MiB | ~50 MiB | `vmbr1` |
| **Home Assistant (LXC 280)** | LXC | 2 vCPU | 1024 MiB | ~450 MiB | `vmbr3` |
| **MQTT Broker (LXC 285)** | LXC | 1 vCPU | 256 MiB | ~30 MiB | `vmbr3` |
| **TOTALS (Full Fleet):** | - | *Shared* | *~10.7 GB ceiling* | **~4.8 GiB Actual** | **Leaves ~2.8 GiB Free** |

> [!TIP]
> **Verdict on Hardware Headroom:**  
> Your ThinkPad i5-3210M with 8 GB RAM is **more than capable** of running your complete planned suite. Because LXC containers do not allocate fixed memory blocks like traditional VMs, your actual steady-state memory usage across the entire fleet will be **under 5.0 GB**, leaving ~3 GB of memory for filesystem disk cache and burst traffic!
