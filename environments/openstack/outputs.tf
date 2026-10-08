output "instance_id" {
  description = "UUID of the created OpenStack server."
  value       = openstack_compute_instance_v2.image.id
}

output "instance_name" {
  description = "Name of the created OpenStack server."
  value       = openstack_compute_instance_v2.image.name
}

output "instance_addresses" {
  description = "Addresses assigned to the OpenStack server, grouped by network."
  value       = openstack_compute_instance_v2.image.network
}

output "instance_ssh_username" {
  description = "Default non-root SSH username from the dib7 image catalog."
  value       = var.image_ssh_username
}

output "selected_catalog_image" {
  description = "Catalog metadata used to create the OpenStack server."
  value = {
    logical_name  = var.image_logical_name
    artifact_id   = var.image_artifact_id
    artifact_type = var.image_artifact_type
    version       = var.image_version
    architecture  = var.image_architecture
    boot_mode     = var.image_boot_mode
    ssh_username  = var.image_ssh_username
    project       = var.image_project
    region        = var.image_region
  }
}
