variable "proxmox_endpoint" {
  type        = string
  default     = "https://192.168.1.2:8006/"
  description = "Proxmox VE API endpoint"
}

variable "node_name" {
  type        = string
  default     = "snowfox"
  description = "Proxmox target cluster node"
}

variable "debian_template" {
  type        = string
  default     = "local:vztmpl/debian-13-standard_13.6-1_amd64.tar.zst"
  description = "Path to Debian 13 template on Proxmox"
}

variable "ssh_public_keys" {
  type        = string
  description = "Authorized SSH public keys to inject into containers"
}
