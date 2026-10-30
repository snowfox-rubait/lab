terraform {
  required_version = ">= 1.5.0"
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.60.0"
    }
  }
}

provider "proxmox" {
  endpoint  = var.proxmox_endpoint
  insecure  = true
  api_token = var.proxmox_api_token
  username  = var.proxmox_api_token == null ? var.proxmox_username : null
  password  = var.proxmox_api_token == null ? var.proxmox_password : null

  ssh {
    agent    = true
    username = "root"
  }
}
