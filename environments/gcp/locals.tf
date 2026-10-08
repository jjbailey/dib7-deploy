locals {
  effective_instance_name = var.instance_name == null ? var.image_logical_name : var.instance_name
  region                  = regex("^(.+)-[a-z]$", var.zone)[0]
  ssh_metadata = var.ssh_public_key == null ? {} : {
    "ssh-keys" = "${var.image_ssh_username}:${trimspace(var.ssh_public_key)}"
  }
}
