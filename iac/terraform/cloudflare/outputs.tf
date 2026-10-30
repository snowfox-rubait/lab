output "kv_namespace_id" {
  value       = cloudflare_workers_kv_namespace.short_links.id
  description = "Created Cloudflare KV namespace ID"
}

output "worker_route" {
  value       = cloudflare_workers_route.shortener_route.pattern
  description = "Active edge route for short URL service"
}

output "short_url_base" {
  value       = "https://${var.short_domain}"
  description = "Base URL for short links"
}
