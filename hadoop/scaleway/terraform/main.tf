locals {
  server_profiles = {
    tiny = {
      bastion = {
        commercial_type = "DEV1-S"
        root_size_gb    = 20
        data_size_gb    = 0
        public          = true
        role            = "bastion"
      }
      gateway = {
        commercial_type = "DEV1-S"
        root_size_gb    = 20
        data_size_gb    = 0
        public          = true
        role            = "gateway"
      }
      master = {
        commercial_type = "DEV1-S"
        root_size_gb    = 20
        data_size_gb    = 20
        public          = false
        role            = "master"
      }
      worker-1 = {
        commercial_type = "DEV1-S"
        root_size_gb    = 20
        data_size_gb    = 20
        public          = false
        role            = "worker"
      }
      worker-2 = {
        commercial_type = "DEV1-S"
        root_size_gb    = 20
        data_size_gb    = 20
        public          = false
        role            = "worker"
      }
      worker-3 = {
        commercial_type = "DEV1-S"
        root_size_gb    = 20
        data_size_gb    = 20
        public          = false
        role            = "worker"
      }
    }

    large = {
      bastion = {
        commercial_type = "DEV1-M"
        root_size_gb    = 40
        data_size_gb    = 0
        public          = true
        role            = "bastion"
      }
      gateway = {
        commercial_type = "DEV1-L"
        root_size_gb    = 80
        data_size_gb    = 0
        public          = true
        role            = "gateway"
      }
      master = {
        commercial_type = "DEV1-XL"
        root_size_gb    = 100
        data_size_gb    = 100
        public          = false
        role            = "master"
      }
      worker-1 = {
        commercial_type = "DEV1-XL"
        root_size_gb    = 80
        data_size_gb    = 500
        public          = false
        role            = "worker"
      }
      worker-2 = {
        commercial_type = "DEV1-XL"
        root_size_gb    = 80
        data_size_gb    = 500
        public          = false
        role            = "worker"
      }
      worker-3 = {
        commercial_type = "DEV1-XL"
        root_size_gb    = 80
        data_size_gb    = 500
        public          = false
        role            = "worker"
      }
    }
  }

  servers = local.server_profiles[var.cluster_size]
  admin_ssh_public_key = trimspace(file(pathexpand(var.admin_ssh_public_key_path)))

  tags = [
    var.project_name,
    "hadoop",
    "teaching",
  ]

  public_servers = {
    for name, server in local.servers : name => server
    if server.public
  }

  data_volumes = {
    for name, server in local.servers : name => server
    if server.data_size_gb > 0
  }

  gateway_cidrs = length(var.student_ssh_cidrs) > 0 ? var.student_ssh_cidrs : [var.teacher_ssh_cidr]

  private_ip_offsets = {
    bastion  = 10
    gateway  = 11
    master   = 12
    worker-1 = 21
    worker-2 = 22
    worker-3 = 23
  }
}

resource "scaleway_vpc_private_network" "hadoop" {
  name   = "${var.project_name}-private"
  region = var.region
  tags   = local.tags

  ipv4_subnet {
    subnet = var.private_subnet
  }
}

resource "scaleway_instance_security_group" "bastion" {
  name                    = "${var.project_name}-bastion-sg"
  inbound_default_policy  = "drop"
  outbound_default_policy = "accept"
  zone                    = var.zone

  inbound_rule {
    action   = "accept"
    port     = 22
    ip_range = var.teacher_ssh_cidr
  }
}

resource "scaleway_instance_security_group" "gateway" {
  name                    = "${var.project_name}-gateway-sg"
  inbound_default_policy  = "drop"
  outbound_default_policy = "accept"
  zone                    = var.zone

  dynamic "inbound_rule" {
    for_each = local.gateway_cidrs
    content {
      action   = "accept"
      port     = 22
      ip_range = inbound_rule.value
    }
  }

  inbound_rule {
    action   = "accept"
    ip_range = var.private_cidr
  }
}

resource "scaleway_instance_security_group" "internal" {
  name                    = "${var.project_name}-internal-sg"
  inbound_default_policy  = "drop"
  outbound_default_policy = "accept"
  zone                    = var.zone

  inbound_rule {
    action   = "accept"
    ip_range = var.private_cidr
  }
}

resource "scaleway_instance_ip" "public" {
  for_each = local.public_servers
  zone     = var.zone
}

resource "scaleway_block_volume" "data" {
  for_each = local.data_volumes

  name       = "${var.project_name}-${each.key}-data"
  zone       = var.zone
  iops       = 5000
  size_in_gb = each.value.data_size_gb
}

resource "scaleway_ipam_ip" "private" {
  for_each = local.servers

  address = cidrhost(var.private_subnet, local.private_ip_offsets[each.key])
  tags    = concat(local.tags, [each.value.role])

  source {
    private_network_id = scaleway_vpc_private_network.hadoop.id
  }
}

resource "scaleway_instance_server" "node" {
  for_each = local.servers

  name              = "${var.project_name}-${each.key}"
  type              = each.value.commercial_type
  image             = var.image
  zone              = var.zone
  tags              = concat(local.tags, [each.value.role])
  enable_dynamic_ip = false
  ip_id             = try(scaleway_instance_ip.public[each.key].id, null)
  security_group_id = each.value.role == "bastion" ? scaleway_instance_security_group.bastion.id : each.value.role == "gateway" ? scaleway_instance_security_group.gateway.id : scaleway_instance_security_group.internal.id
  additional_volume_ids = try([scaleway_block_volume.data[each.key].id], [])

  root_volume {
    size_in_gb  = each.value.root_size_gb
    volume_type = "sbs_volume"
  }

  user_data = {
    cloud-init = templatefile("${path.module}/cloud-init.yaml.tftpl", {
      ssh_public_key = local.admin_ssh_public_key
    })
  }
}

resource "scaleway_instance_private_nic" "node" {
  for_each = local.servers

  server_id          = scaleway_instance_server.node[each.key].id
  private_network_id = scaleway_vpc_private_network.hadoop.id
  ipam_ip_ids        = [scaleway_ipam_ip.private[each.key].id]
  zone               = var.zone
}
