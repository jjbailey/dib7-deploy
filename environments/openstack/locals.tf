locals {
  effective_instance_name = var.instance_name != null ? var.instance_name : var.image_logical_name
  effective_key_pair      = var.key_pair != null ? var.key_pair : var.image_ssh_username
  # Treat blank launch settings as unset so only the chosen selector is sent.
  network_name = var.network_name != null && trimspace(var.network_name) != "" ? var.network_name : null
  network_id   = var.network_id != null && trimspace(var.network_id) != "" ? var.network_id : null
}
