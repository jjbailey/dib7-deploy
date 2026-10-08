data "vsphere_datacenter" "target" {
  name = var.datacenter
}

data "vsphere_virtual_machine" "image_template" {
  name          = var.image_artifact_id
  datacenter_id = data.vsphere_datacenter.target.id
  folder        = var.template_folder
}

data "vsphere_resource_pool" "target" {
  count         = var.resource_pool != null && trimspace(var.resource_pool) != "" ? 1 : 0
  name          = var.resource_pool
  datacenter_id = data.vsphere_datacenter.target.id
}

data "vsphere_host" "compute" {
  count         = var.resource_pool == null || trimspace(var.resource_pool) == "" ? 1 : 0
  name          = var.compute_host != null && trimspace(var.compute_host) != "" ? var.compute_host : null
  datacenter_id = data.vsphere_datacenter.target.id
}

data "vsphere_datastore" "target" {
  name          = var.datastore
  datacenter_id = data.vsphere_datacenter.target.id
}

data "vsphere_network" "target" {
  name          = var.network
  datacenter_id = data.vsphere_datacenter.target.id
}

resource "terraform_data" "image_revision" {
  triggers_replace = {
    logical_name = var.image_logical_name
    artifact_id  = var.image_artifact_id
    version      = var.image_version
  }
}

resource "vsphere_virtual_machine" "image" {
  name             = local.effective_vm_name
  resource_pool_id = local.effective_resource_pool_id
  datastore_id     = data.vsphere_datastore.target.id
  folder           = var.vm_folder
  num_cpus         = var.num_cpus
  memory           = var.memory_mb
  guest_id         = local.effective_guest_id
  firmware         = local.firmware
  scsi_type        = var.scsi_type
  extra_config     = local.guest_extra_config

  network_interface {
    network_id   = data.vsphere_network.target.id
    adapter_type = "vmxnet3"
  }

  disk {
    label            = "Hard disk 1"
    size             = var.disk_size_gb
    thin_provisioned = var.thin_provisioned
  }

  clone {
    template_uuid = data.vsphere_virtual_machine.image_template.id
  }

  lifecycle {
    replace_triggered_by = [terraform_data.image_revision]

    precondition {
      condition = (
        var.target_vcenter_key == null ||
        lookup(var.image_scope, "vcenter", var.target_vcenter_key) == var.target_vcenter_key
      )
      error_message = "The selected Vault vCenter does not match the vCenter recorded in the image catalog scope."
    }

    precondition {
      condition     = var.ssh_public_key == null || (var.image_ssh_username != null && trimspace(var.image_ssh_username) != "")
      error_message = "A public key was provided, but the catalog has no image_ssh_username for this image."
    }
  }
}
