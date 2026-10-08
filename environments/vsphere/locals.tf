locals {
  effective_vm_name = var.vm_name == null ? var.image_logical_name : var.vm_name
  effective_resource_pool_id = (
    var.resource_pool != null && trimspace(var.resource_pool) != ""
    ? data.vsphere_resource_pool.target[0].id
    : data.vsphere_host.compute[0].resource_pool_id
  )
  effective_guest_id = var.guest_id != null ? var.guest_id : data.vsphere_virtual_machine.image_template.guest_id
  firmware           = var.image_boot_mode == "uefi" ? "efi" : "bios"

  guest_metadata = var.ssh_public_key == null ? null : {
    "instance-id"      = local.effective_vm_name
    "local-hostname"   = local.effective_vm_name
    "public-keys-data" = trimspace(var.ssh_public_key)
  }
  guest_extra_config = local.guest_metadata == null ? {} : {
    "guestinfo.metadata"          = base64encode(jsonencode(local.guest_metadata))
    "guestinfo.metadata.encoding" = "base64"
  }
}
