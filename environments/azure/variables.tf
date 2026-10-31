variable "image_logical_name" {
  description = "Logical image name selected from the dib7 catalog."
  type        = string
}

variable "image_artifact_id" {
  description = "Azure managed image resource ID selected from the catalog."
  type        = string

  validation {
    condition     = can(regex("(?i)^/subscriptions/[^/]+/resourceGroups/[^/]+/providers/Microsoft\\.Compute/images/[^/]+$", var.image_artifact_id))
    error_message = "image_artifact_id must be an Azure managed image resource ID."
  }
}

variable "image_artifact_type" {
  description = "Catalog artifact type; Azure deployments require managed_image."
  type        = string

  validation {
    condition     = var.image_artifact_type == "managed_image"
    error_message = "image_artifact_type must be managed_image for Azure."
  }
}

variable "image_version" {
  description = "Catalog version selected by the Azure tfvars generator."
  type        = string
}

variable "image_architecture" {
  description = "Architecture recorded for the selected catalog image."
  type        = string
}

variable "image_boot_mode" {
  description = "Boot mode recorded for the selected catalog image."
  type        = string
}

variable "image_ssh_username" {
  description = "Default non-root SSH login recorded for the catalog image; used as the VM admin username."
  type        = string
  default     = null
  nullable    = true
}

variable "image_project" {
  description = "Azure subscription recorded as the catalog image owner."
  type        = string
  default     = null
  nullable    = true
}

variable "image_region" {
  description = "Azure location containing the selected managed image. The VM is created in the same location."
  type        = string

  validation {
    condition     = length(trimspace(var.image_region)) > 0
    error_message = "image_region must be set by the Azure catalog entry."
  }
}

variable "image_scope" {
  description = "Additional scope metadata recorded for the catalog image."
  type        = map(string)
  default     = {}
}

variable "resource_group_name" {
  description = "Existing resource group for the VM and its network resources. Defaults to resource_group from the selected Ansible Vault entry."
  type        = string

  validation {
    condition     = length(trimspace(var.resource_group_name)) > 0
    error_message = "resource_group_name must name an existing Azure resource group."
  }
}

variable "instance_name" {
  description = "Azure VM name. Defaults to the catalog logical image name."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition     = var.instance_name == null || (length(var.instance_name) <= 64 && can(regex("^[a-z0-9]([-a-z0-9]*[a-z0-9])?$", var.instance_name)))
    error_message = "instance_name must be lowercase letters, digits, and hyphens, at most 64 characters."
  }
}

variable "vm_size" {
  description = "Azure VM size available in the image location; it must support Hyper-V Gen2 for UEFI images."
  type        = string
  default     = "Standard_B2als_v2"
}

variable "zone" {
  description = "Optional availability zone (1, 2, or 3). Null places the VM without a zone."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition     = var.zone == null || contains(["1", "2", "3"], var.zone)
    error_message = "zone must be 1, 2, 3, or null."
  }
}

variable "subnet_id" {
  description = "Resource ID of an existing virtual network subnet in the image location."
  type        = string

  validation {
    condition     = can(regex("(?i)^/subscriptions/[^/]+/resourceGroups/[^/]+/providers/Microsoft\\.Network/virtualNetworks/[^/]+/subnets/[^/]+$", var.subnet_id))
    error_message = "subnet_id must be an Azure subnet resource ID."
  }
}

variable "network_security_group_id" {
  description = "Optional existing network security group to attach to the VM's network interface."
  type        = string
  default     = null
  nullable    = true
}

variable "assign_public_ip" {
  description = "Whether to create a static Standard public IPv4 address. Standard addresses deny inbound traffic unless a network security group allows it."
  type        = bool
  default     = true
}

variable "key_name" {
  description = "Optional existing Azure SSH public key resource name. Defaults to the catalog SSH username."
  type        = string
  default     = null
  nullable    = true
}

variable "key_resource_group_name" {
  description = "Resource group holding the SSH public key resource. Defaults to resource_group_name."
  type        = string
  default     = null
  nullable    = true
}

variable "ssh_public_key" {
  description = "Optional OpenSSH public key line. When set, it is used instead of looking up an SSH public key resource."
  type        = string
  default     = null
  nullable    = true
}

variable "os_disk_size_gb" {
  description = "Optional OS disk size; null inherits the source image size."
  type        = number
  default     = null
  nullable    = true
}

variable "os_disk_storage_account_type" {
  description = "Managed disk type for the OS disk."
  type        = string
  default     = "StandardSSD_LRS"
}

variable "boot_diagnostics" {
  description = "Enable boot diagnostics with managed storage, which provides the serial console and boot screenshots."
  type        = bool
  default     = true
}

variable "tags" {
  description = "Additional Azure tags. Catalog provenance tags are added to the VM automatically."
  type        = map(string)
  default     = {}
}
