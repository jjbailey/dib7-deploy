output "instance_id" {
  description = "ID of the launched EC2 instance."
  value       = aws_instance.image.id
}

output "instance_ami_id" {
  description = "AMI ID used to launch the instance."
  value       = aws_instance.image.ami
}

output "instance_private_ip" {
  description = "Private IPv4 address assigned to the instance."
  value       = aws_instance.image.private_ip
}

output "instance_public_ip" {
  description = "Public IPv4 address, if AWS assigned one."
  value       = aws_instance.image.public_ip
}

output "instance_ssh_username" {
  description = "Default non-root SSH login recorded for the catalog image."
  value       = var.image_ssh_username
}

output "instance_key_name" {
  description = "EC2 key pair used for SSH access, if configured."
  value       = local.effective_key_name
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
