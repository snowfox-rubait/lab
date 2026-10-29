variable "cloudflare_api_token" {
  type        = string
  description = "Cloudflare API Token with Zone.DNS:Edit permissions for snowfox.live"
  sensitive   = true
}

variable "domain" {
  type        = string
  default     = "snowfox.live"
  description = "Apex domain name"
}

variable "email_address" {
  type        = string
  default     = "admin@snowfox.live"
  description = "Contact email for Let's Encrypt certificate expiration alerts"
}

variable "nginx_safe_host" {
  type        = string
  default     = "10.10.10.10"
  description = "IP address of nginx-safe LXC 201 container"
}

variable "proxmox_host" {
  type        = string
  default     = "192.168.1.2"
  description = "Proxmox hypervisor jump host IP"
}
