# ==============================================================================
# Declarative Let's Encrypt Wildcard TLS Certificate via Terraform
# Domain: *.snowfox.live & snowfox.live
# Provider: vancluever/acme with Cloudflare DNS-01 Challenge
# Target: Deployed directly into LXC 201 (10.10.10.10)
# ==============================================================================

# 1. ACME Account Private Key
resource "tls_private_key" "acme_account_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

# 2. ACME Registration with Let's Encrypt
resource "acme_registration" "reg" {
  account_key_pem = tls_private_key.acme_account_key.private_key_pem
  email_address   = var.email_address
}

# 3. Request Wildcard Certificate via Cloudflare DNS-01
resource "acme_certificate" "wildcard_cert" {
  account_key_pem           = acme_registration.reg.account_key_pem
  common_name               = "*.${var.domain}"
  subject_alternative_names = [var.domain]
  key_type                  = "2048"

  dns_challenge {
    provider = "cloudflare"

    config = {
      CF_DNS_API_TOKEN = var.cloudflare_api_token
    }
  }
}

# 4. Deploy Certificate and Private Key to LXC 201 & Reload Nginx
resource "null_resource" "deploy_to_nginx_safe" {
  triggers = {
    cert_sha256 = sha256(acme_certificate.wildcard_cert.certificate_pem)
  }

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      # Write fullchain (cert + intermediate issuer) and private key to temporary files
      CERT_CHAIN="${acme_certificate.wildcard_cert.certificate_pem}${acme_certificate.wildcard_cert.issuer_pem}"
      PRIV_KEY="${acme_certificate.wildcard_cert.private_key_pem}"

      # Stream securely to LXC 201 via Proxmox Jump Host
      ssh -o StrictHostKeyChecking=accept-new -J root@${var.proxmox_host} root@${var.nginx_safe_host} \
        "mkdir -p /etc/letsencrypt/live/${var.domain} && \
         cat <<'EOF_CERT' > /etc/letsencrypt/live/${var.domain}/fullchain.pem
$CERT_CHAIN
EOF_CERT
         cat <<'EOF_KEY' > /etc/letsencrypt/live/${var.domain}/privkey.pem
$PRIV_KEY
EOF_KEY
         chmod 600 /etc/letsencrypt/live/${var.domain}/privkey.pem && \
         chmod 644 /etc/letsencrypt/live/${var.domain}/fullchain.pem && \
         nginx -t && systemctl reload nginx"
    EOT
  }

  depends_on = [acme_certificate.wildcard_cert]
}
