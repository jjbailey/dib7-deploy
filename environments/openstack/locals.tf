locals {
  effective_instance_name = var.instance_name != null ? var.instance_name : var.image_logical_name
  effective_key_pair      = var.key_pair != null ? var.key_pair : var.image_ssh_username
}
