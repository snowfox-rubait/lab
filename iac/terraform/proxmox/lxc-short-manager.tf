# ==============================================================================
# Declarative Proxmox LXC Definition: LXC 225 (short-manager)
# Zone: vmbr1 (Safe Internal)
# IP: 10.10.10.35 / FQDN: short.internal.lab
# ==============================================================================

resource "proxmox_virtual_environment_container" "short_manager" {
  node_name     = var.node_name
  vm_id         = 225
  description   = "Personal URL Shortener 2-Page Web Admin UI (Project 13) - Terraform Managed"
  unprivileged  = true
  started       = true
  start_on_boot = true

  initialization {
    hostname = "short-manager"

    dns {
      servers = ["192.168.1.135", "1.1.1.1"]
    }

    ip_config {
      ipv4 {
        address = "10.10.10.35/24"
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
    dedicated = 512
    swap      = 512
  }

  disk {
    datastore_id = "local-lvm"
    size         = 4
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
}
