# ==============================================================================
# Declarative Proxmox LXC Definition: LXC 240 (n8n)
# Zone: vmbr1 (Safe Internal)
# IP: 10.10.10.25 / FQDN: n8n.internal.lab (n8n.snowfox.live)
# ==============================================================================

resource "proxmox_virtual_environment_container" "n8n" {
  node_name     = var.node_name
  vm_id         = 240
  description   = "n8n Workflow Automation Hub (Project 08) - Native Node.js in LXC - Terraform Managed"
  unprivileged  = true
  started       = true
  start_on_boot = true

  initialization {
    hostname = "n8n"

    dns {
      servers = ["192.168.1.135", "1.1.1.1"]
    }

    ip_config {
      ipv4 {
        address = "10.10.10.25/24"
        gateway = "10.10.10.1"
      }
    }

    user_account {
      keys = [trimspace(var.ssh_public_keys)]
    }
  }

  cpu {
    cores = 1
  }

  memory {
    dedicated = 1024
    swap      = 512
  }

  disk {
    datastore_id = "local-lvm"
    size         = 8
  }

  network_interface {
    name    = "eth0"
    bridge  = "vmbr1"
    enabled = true
  }

  operating_system {
    template_file_id = var.debian_template
    type             = "debian"
  }

  features {
    nesting = true
  }

  lifecycle {
    prevent_destroy = true
    ignore_changes = [
      operating_system[0].template_file_id,
      initialization[0].user_account,
      unprivileged,
    ]
  }
}

