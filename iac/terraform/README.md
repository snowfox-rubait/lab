# 🏗️ Homelab Terraform Infrastructure as Code (IaC)

> **Terraform Version:** `>= 1.5.0` (Installed locally at `/usr/bin/terraform`)  
> **Target Providers:** `cloudflare/cloudflare` & `bpg/proxmox`  
> **Role:** Declarative Day-0 / Day-1 resource provisioning (Proxmox LXC containers & Cloudflare Serverless Edge).

---

## 📁 Architecture & Module Structure

```
iac/terraform/
├── acme-wildcard/               # Automated Wildcard TLS Certificate (DNS-01)
│   ├── versions.tf              # vancluever/acme provider
│   ├── main.tf                  # Let's Encrypt Wildcard (*.snowfox.live) + LXC deployer
│   ├── variables.tf             # Cloudflare token, domain, email
│   ├── outputs.tf               # Issued certificate attributes
│   └── terraform.tfvars.example # Credentials template
├── cloudflare/                  # Cloudflare Edge Infrastructure
│   ├── versions.tf              # Cloudflare provider v4.x
│   ├── main.tf                  # Worker script, KV namespace, WAF BD rule, DNS records
│   ├── variables.tf             # Zone ID, Account ID, API tokens
│   ├── outputs.tf               # KV namespace IDs, active edge routes
│   └── terraform.tfvars.example # Credential parameters template
└── proxmox/                     # Proxmox Hypervisor Infrastructure
    ├── versions.tf              # bpg/proxmox provider
    ├── lxc-nginx-safe.tf        # LXC 201 (nginx-safe on vmbr1: 10.10.10.10)
    ├── lxc-short-manager.tf     # LXC 225 (short-manager on vmbr1: 10.10.10.35)
    ├── variables.tf             # PVE endpoint, node, Debian template, SSH keys
    ├── outputs.tf               # Container IPs & identifiers
    └── terraform.tfvars.example # Proxmox credentials template
```

---

## ⚡ Division of Responsibility: Terraform vs. pyinfra

| Layer | Tool | Responsibilities |
| :--- | :--- | :--- |
| **Day-0 / Day-1: Infrastructure Provisioning** | **Terraform** | - Creates Proxmox LXC containers (cores, memory, disks, bridges `vmbr1`–`vmbr7`).<br>- Creates Cloudflare Workers, KV namespaces, routes, and Bangladesh WAF rules. |
| **Day-2: Configuration Management** | **pyinfra** | - Installs Linux packages inside containers (`nginx`, `certbot`, `python3`).<br>- Deploys systemd unit files, virtual host files, and cron jobs.<br>- Executes OpenWrt UCI network & firewall configuration via SSH. |

---

## 🚀 Execution Runbook

### 1. Cloudflare Infrastructure Provisioning
```bash
cd iac/terraform/cloudflare
cp terraform.tfvars.example terraform.tfvars
# Fill in cloudflare_api_token, cloudflare_account_id, cloudflare_zone_id

terraform init
terraform plan
terraform apply
```

### 2. Proxmox Container Provisioning
```bash
cd iac/terraform/proxmox
cp terraform.tfvars.example terraform.tfvars
# Fill in ssh_public_keys and verify node_name

terraform init
terraform plan
terraform apply
```

### 3. Wildcard TLS Certificate Issuance & Nginx Deployment
```bash
cd iac/terraform/acme-wildcard
cp terraform.tfvars.example terraform.tfvars
# Fill in cloudflare_api_token

terraform init
terraform plan
terraform apply
```
*(Automatically registers with Let's Encrypt, creates DNS-01 verification TXT records on Cloudflare, deploys certs into LXC 201, and reloads Nginx).*

