output "instance_uuid" {
  description = "vSphere instance UUID for the launched virtual machine."
  value       = vsphere_virtual_machine.image.uuid
}

output "instance_moid" {
  description = "vCenter managed object ID for the launched virtual machine."
  value       = vsphere_virtual_machine.image.moid
}

output "instance_name" {
  description = "Inventory name of the launched virtual machine."
  value       = vsphere_virtual_machine.image.name
}

output "instance_default_ip" {
  description = "Default IP reported by VMware Tools, when available."
  value       = vsphere_virtual_machine.image.default_ip_address
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
