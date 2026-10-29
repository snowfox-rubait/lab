# ==============================================================================
# Declarative Proxmox LXC Definition: LXC 201 (nginx-safe)
# Zone: vmbr1 (Safe Internal)
# IP: 10.10.10.10 / FQDN: internal.lab (*.snowfox.live)
# ==============================================================================

resource "proxmox_virtual_environment_container" "nginx_safe" {
  node_name     = var.node_name
  vm_id         = 201
  description   = "Safe Internal Reverse Proxy & Split-Horizon TLS (*.snowfox.live) - Terraform Managed"
  unprivileged  = true
  started       = true
  start_on_boot = true

  initialization {
    hostname = "nginx-safe"

    dns {
      servers = ["192.168.1.135", "1.1.1.1"]
    }

    ip_config {
      ipv4 {
        address = "10.10.10.10/24"
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
