resource "terraform_data" "image_revision" {
  triggers_replace = {
    logical_name = var.image_logical_name
    artifact_id  = var.image_artifact_id
    version      = var.image_version
  }
}

data "azurerm_ssh_public_key" "login" {
  count = var.ssh_public_key == null ? 1 : 0

  name                = local.effective_key_name
  resource_group_name = var.key_resource_group_name == null ? var.resource_group_name : var.key_resource_group_name
}

resource "azurerm_public_ip" "image" {
  count = var.assign_public_ip ? 1 : 0

  name                = "${local.effective_instance_name}-ip"
  resource_group_name = var.resource_group_name
  location            = local.location
  allocation_method   = "Static"
  sku                 = "Standard"
  zones               = var.zone == null ? null : [var.zone]
  tags                = var.tags
}

resource "azurerm_network_interface" "image" {
  name                = "${local.effective_instance_name}-nic"
  resource_group_name = var.resource_group_name
  location            = local.location
  tags                = var.tags

  ip_configuration {
    name                          = "primary"
    subnet_id                     = var.subnet_id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = var.assign_public_ip ? azurerm_public_ip.image[0].id : null
  }
}

resource "azurerm_network_interface_security_group_association" "image" {
  count = var.network_security_group_id == null ? 0 : 1

  network_interface_id      = azurerm_network_interface.image.id
  network_security_group_id = var.network_security_group_id
}

resource "azurerm_linux_virtual_machine" "image" {
  name                  = local.effective_instance_name
  resource_group_name   = var.resource_group_name
  location              = local.location
  size                  = var.vm_size
  zone                  = var.zone
  source_image_id       = var.image_artifact_id
  network_interface_ids = [azurerm_network_interface.image.id]

  admin_username                  = var.image_ssh_username
  disable_password_authentication = true

  admin_ssh_key {
    username   = var.image_ssh_username
    public_key = local.admin_ssh_public_key
  }

  # DIB7 images provision through cloud-init and do not ship the Azure Linux
  # agent, so VM extensions are unavailable.
  provision_vm_agent         = false
  allow_extension_operations = false

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = var.os_disk_storage_account_type
    disk_size_gb         = var.os_disk_size_gb
  }

  dynamic "boot_diagnostics" {
    for_each = var.boot_diagnostics ? [true] : []
    content {}
  }

  tags = merge(var.tags, {
    dib7_image_name = var.image_logical_name
    dib7_image_run  = var.image_version
  })

  lifecycle {
    replace_triggered_by = [terraform_data.image_revision]

    precondition {
      condition     = var.image_ssh_username != null && length(trimspace(var.image_ssh_username)) > 0
      error_message = "The catalog has no image_ssh_username for this image; Azure requires an admin username."
    }
  }
}
