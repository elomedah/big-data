locals {
  nodes = {
    for name, server in scaleway_instance_server.node : name => {
      name       = name
      role       = local.servers[name].role
      public_ip  = try(scaleway_instance_ip.public[name].address, null)
      private_ip = scaleway_ipam_ip.private[name].address
    }
  }

  bastion_ip = scaleway_instance_ip.public["bastion"].address
}

output "nodes" {
  description = "Cluster nodes with public and private addresses."
  value       = local.nodes
}

output "bastion_public_ip" {
  description = "Public IP used as the SSH jump host."
  value       = local.bastion_ip
}

output "gateway_public_ip" {
  description = "Public IP for student SSH access."
  value       = scaleway_instance_ip.public["gateway"].address
}

output "ansible_inventory" {
  description = "Inventory to write to ../ansible/inventory.ini."
  value = templatefile("${path.module}/inventory.ini.tftpl", {
    nodes      = local.nodes
    bastion_ip = local.bastion_ip
  })
}

output "bastion_ansible_inventory" {
  description = "Inventory to copy to the bastion when Ansible runs from the bastion."
  value = templatefile("${path.module}/inventory-bastion.ini.tftpl", {
    nodes = local.nodes
  })
}
