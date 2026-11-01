locals {
  effective_instance_name = var.instance_name == null ? var.image_logical_name : var.instance_name
  # A managed image can only be used in the region that holds it.
  location = var.image_region
  # DIB7 images conventionally use an SSH public key resource named after the
  # default login. An explicit launch setting can override that choice.
  effective_key_name   = var.key_name != null ? var.key_name : var.image_ssh_username
  admin_ssh_public_key = var.ssh_public_key != null ? trimspace(var.ssh_public_key) : trimspace(data.azurerm_ssh_public_key.login[0].public_key)
}
