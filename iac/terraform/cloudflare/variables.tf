variable "cloudflare_api_token" {
  type        = string
  default     = null
  description = "Cloudflare API Token with Zone.DNS (Edit), Worker (Edit), and Account.KV (Edit) permissions"
  sensitive   = true
}

variable "cloudflare_email" {
  type        = string
  default     = null
  description = "Cloudflare Account Email"
}

variable "cloudflare_api_key" {
  type        = string
  default     = null
  description = "Cloudflare Global API Key"
  sensitive   = true
}

variable "cloudflare_account_id" {
  type        = string
  description = "Cloudflare Account ID"
}

variable "cloudflare_zone_id" {
  type        = string
  description = "Cloudflare Zone ID for snowfox.live"
}

variable "domain" {
  type        = string
  default     = "snowfox.live"
  description = "Apex domain name"
}

variable "short_domain" {
  type        = string
  default     = "short.snowfox.live"
  description = "Custom hostname for URL shortener service"
}

variable "shortener_secret_token" {
  type        = string
  description = "Master bearer token for private vmbr1 management UI API calls"
  sensitive   = true
}
