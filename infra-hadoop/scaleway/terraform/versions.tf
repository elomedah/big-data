terraform {
  required_version = ">= 1.6.0"

  required_providers {
    scaleway = {
      source  = "scaleway/scaleway"
      version = "~> 2.59"
    }
  }
}

provider "scaleway" {
  zone   = var.zone
  region = var.region
}
