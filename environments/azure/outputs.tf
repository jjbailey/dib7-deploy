output "instance_id" {
  description = "Resource ID of the launched Azure VM."
  value       = azurerm_linux_virtual_machine.image.id
}

output "instance_name" {
  description = "Name of the launched Azure VM."
  value       = azurerm_linux_virtual_machine.image.name
}

output "instance_private_ip" {
  description = "Private IPv4 address assigned to the VM's network interface."
  value       = azurerm_linux_virtual_machine.image.private_ip_address
}

output "instance_public_ip" {
  description = "Static public IPv4 address, when assign_public_ip is enabled."
  value       = try(azurerm_public_ip.image[0].ip_address, null)
}

output "instance_ssh_username" {
  description = "Default non-root SSH login recorded for the catalog image."
  value       = var.image_ssh_username
}

output "selected_catalog_image" {
  description = "Catalog metadata for the image used by this deployment."
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
    scope         = var.image_scope
  }
}
