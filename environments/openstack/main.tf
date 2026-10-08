resource "openstack_compute_instance_v2" "image" {
  name              = local.effective_instance_name
  image_id          = var.image_artifact_id
  flavor_name       = var.flavor_name
  key_pair          = local.effective_key_pair
  security_groups   = var.security_groups
  availability_zone = var.availability_zone
  metadata = merge(var.metadata, {
    dib7_image_name    = var.image_logical_name
    dib7_image_version = var.image_version
  })

  network {
    name = var.network_name
    uuid = var.network_id
  }

  lifecycle {
    precondition {
      condition = (
        (var.network_name != null && trimspace(var.network_name) != "") !=
        (var.network_id != null && trimspace(var.network_id) != "")
      )
      error_message = "Set exactly one of network_name or network_id in the OpenStack launch settings."
    }

    precondition {
      condition = (
        var.target_region == null ||
        var.image_region == var.target_region
      )
      error_message = "The selected Vault region does not match the region recorded in the image catalog."
    }
  }
}
