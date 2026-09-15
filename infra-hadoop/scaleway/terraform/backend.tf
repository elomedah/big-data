terraform {
  backend "s3" {
    key                         = "scaleway/hadoop/terraform.tfstate"
    region                      = "fr-par"
    endpoints = {
      s3 = "https://s3.fr-par.scw.cloud"
    }
    force_path_style            = true
    skip_credentials_validation = true
    skip_region_validation      = true
    skip_requesting_account_id  = true
    use_lockfile                = true
  }
}
