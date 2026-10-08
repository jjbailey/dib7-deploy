resource "terraform_data" "image_revision" {
  triggers_replace = {
    logical_name = var.image_logical_name
    artifact_id  = var.image_artifact_id
    version      = var.image_version
  }
}

resource "google_compute_instance" "image" {
  name                      = local.effective_instance_name
  project                   = var.project_id
  zone                      = var.zone
  machine_type              = var.machine_type
  tags                      = var.network_tags
  metadata                  = merge(var.metadata, local.ssh_metadata)
  allow_stopping_for_update = var.allow_stopping_for_update

  labels = merge(var.labels, {
    dib7_image_name = lower(var.image_logical_name)
    dib7_image_run  = lower(var.image_version)
  })

  boot_disk {
    auto_delete = true

    initialize_params {
      image = var.image_artifact_id
      size  = var.boot_disk_size_gb
      type  = var.boot_disk_type
    }
  }

  network_interface {
    network    = var.network
    subnetwork = var.subnetwork

    dynamic "access_config" {
      for_each = var.assign_public_ip ? [true] : []
      content {}
    }
  }

  dynamic "service_account" {
    for_each = var.service_account_email == null ? [] : [var.service_account_email]
    content {
      email  = service_account.value
      scopes = var.service_account_scopes
    }
  }

  lifecycle {
    replace_triggered_by = [terraform_data.image_revision]

    precondition {
      condition     = var.network != null || var.subnetwork != null
      error_message = "Set network or subnetwork; a Compute Engine instance needs a VPC attachment."
    }

    precondition {
      condition     = var.ssh_public_key == null || (var.image_ssh_username != null && length(trimspace(var.image_ssh_username)) > 0)
      error_message = "A public key was provided, but the catalog has no image_ssh_username for this image."
    }
  }
}
