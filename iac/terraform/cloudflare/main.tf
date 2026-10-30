# ==============================================================================
# Cloudflare Infrastructure for Project 13: Personal URL Shortener
# Edge Redirection Worker + KV Namespace + Strict Bangladesh Geo-Fence
# ==============================================================================

# 1. Cloudflare Workers KV Namespace for link storage
resource "cloudflare_workers_kv_namespace" "short_links" {
  account_id = var.cloudflare_account_id
  title      = "SHORT_LINKS"
}

# 2. Cloudflare Worker Script Deployment
resource "cloudflare_workers_script" "shortener" {
  account_id = var.cloudflare_account_id
  name       = "snowfox-shortener"
  content    = file("${path.module}/../../../projects/13-personal-url-shortener/worker/worker.js")
  module     = true

  # KV Namespace Binding
  kv_namespace_binding {
    name         = "SHORT_LINKS"
    namespace_id = cloudflare_workers_kv_namespace.short_links.id
  }

  # Encrypted Secret Token Binding
  secret_text_binding {
    name = "SHORTENER_SECRET_TOKEN"
    text = var.shortener_secret_token
  }

  # Plaintext Environment Variables
  plain_text_binding {
    name = "DEFAULT_FALLBACK_URL"
    text = "https://${var.domain}"
  }
}

# 3. Cloudflare Worker Route Binding
resource "cloudflare_workers_route" "shortener_route" {
  zone_id     = var.cloudflare_zone_id
  pattern     = "${var.short_domain}/*"
  script_name = cloudflare_workers_script.shortener.name
}

# 4. DNS CNAME Record for short.snowfox.live pointing to Worker
resource "cloudflare_record" "short_domain" {
  zone_id = var.cloudflare_zone_id
  name    = "short"
  type    = "CNAME"
  content = "100::" # Standard Cloudflare Worker dummy target or apex
  proxied = true
  comment = "Personal URL Shortener Edge Worker (Terraform Managed)"
}

# 5. Strict Bangladesh-Only WAF Custom Rule (Layer 1 Defense-in-Depth)
resource "cloudflare_ruleset" "waf_bd_geofence" {
  zone_id     = var.cloudflare_zone_id
  name        = "snowfox-bd-geofence"
  description = "Block traffic to short.snowfox.live originating outside Bangladesh"
  kind        = "zone"
  phase       = "http_request_firewall_custom"

  rules {
    action      = "block"
    expression  = "(http.host eq \"${var.short_domain}\" and ip.geoip.country ne \"BD\")"
    description = "Block non-Bangladesh callers to short.snowfox.live"
    enabled     = true
  }
}
