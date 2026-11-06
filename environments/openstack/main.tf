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
    name = local.network_name
    uuid = local.network_id
  }

  lifecycle {
    precondition {
      condition     = (local.network_name != null) != (local.network_id != null)
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

# dib7 republishes by deleting the image by name and uploading a new one,
# so an older tfvars file can name a UUID that no longer exists. The compute
# instance does not validate image_id until apply; this reports it during plan.
# It is a check rather than a precondition so an instance whose image was
# already replaced can still be planned and destroyed. Glance names images
# after the catalog logical name, and the provider cannot filter by ID.
check "catalog_image_available" {
  data "openstack_images_image_ids_v2" "catalog" {
    name   = var.image_logical_name
    region = var.image_region
  }

  assert {
    condition     = contains(data.openstack_images_image_ids_v2.catalog.ids, var.image_artifact_id)
    error_message = "Glance image ${var.image_artifact_id} (${var.image_logical_name} catalog version ${var.image_version}) is not available to this project; dib7 may have republished it. Regenerate the tfvars from the current catalog before creating or replacing the instance."
  }
}
