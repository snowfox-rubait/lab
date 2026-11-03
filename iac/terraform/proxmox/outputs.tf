output "nginx_safe_ip" {
  value       = "10.10.10.10"
  description = "Safe Internal Reverse Proxy IP"
}

output "short_manager_ip" {
  value       = "10.10.10.35"
  description = "URL Shortener Admin UI IP"
}

output "n8n_ip" {
  value       = "10.10.10.25"
  description = "n8n Automation Engine IP"
}

output "mermaid_ip" {
  value       = "10.10.10.26"
  description = "Mermaid Live Editor Server IP"
}
