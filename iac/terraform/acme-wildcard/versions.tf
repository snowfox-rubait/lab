terraform {
  required_version = ">= 1.5.0"
  required_providers {
    acme = {
      source  = "vancluever/acme"
      version = "~> 2.24.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}

provider "acme" {
  # Let's Encrypt Production ACME v2 Directory
  server_url = "https://acme-v02.api.letsencrypt.org/directory"
}
