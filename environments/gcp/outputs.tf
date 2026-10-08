output "instance_id" {
  description = "Numeric ID of the launched Compute Engine instance."
  value       = google_compute_instance.image.instance_id
}

output "instance_name" {
  description = "Name of the launched Compute Engine instance."
  value       = google_compute_instance.image.name
}

output "instance_self_link" {
  description = "Self-link of the launched Compute Engine instance."
  value       = google_compute_instance.image.self_link
}

output "instance_private_ip" {
  description = "Internal IPv4 address assigned to the instance."
  value       = google_compute_instance.image.network_interface[0].network_ip
}

output "instance_public_ip" {
  description = "Ephemeral external IPv4 address, when assign_public_ip is enabled."
  value       = try(google_compute_instance.image.network_interface[0].access_config[0].nat_ip, null)
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
