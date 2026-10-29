output "certificate_domain" {
  value       = acme_certificate.wildcard_cert.certificate_domain
  description = "Domain name on issued certificate"
}

output "certificate_url" {
  value       = acme_certificate.wildcard_cert.certificate_url
  description = "Let's Encrypt Certificate Order URL"
}

output "expires_at" {
  value       = timeadd(timestamp(), "2160h") # 90 days default
  description = "Estimated expiration date (auto-renewed via Terraform)"
}
