variable "image_logical_name" {
  description = "Logical image name selected from the dib7 catalog."
  type        = string
}

variable "image_artifact_id" {
  description = "vSphere inventory VM template name recorded in the catalog."
  type        = string
}

variable "image_artifact_type" {
  description = "Catalog artifact type; vSphere deployments require content_library_template."
  type        = string

  validation {
    condition     = var.image_artifact_type == "content_library_template"
    error_message = "image_artifact_type must be content_library_template for vSphere."
  }
}

variable "image_version" {
  description = "Catalog version selected by the vSphere tfvars generator."
  type        = string
}

variable "image_architecture" {
  description = "Architecture recorded for the selected catalog image."
  type        = string
}

variable "image_boot_mode" {
  description = "Boot mode recorded for the selected catalog image."
  type        = string

  validation {
    condition     = contains(["uefi", "bios"], var.image_boot_mode)
    error_message = "image_boot_mode must be uefi or bios."
  }
}

variable "image_ssh_username" {
  description = "Default non-root SSH login recorded for the catalog image."
  type        = string
  default     = null
  nullable    = true
}

variable "image_project" {
  description = "Project recorded as the catalog image owner, if present."
  type        = string
  default     = null
  nullable    = true
}

variable "image_region" {
  description = "Region recorded for the catalog image, if present."
  type        = string
  default     = null
  nullable    = true
}

variable "image_scope" {
  description = "Additional scope metadata recorded for the catalog image."
  type        = map(string)
  default     = {}
}

variable "target_vcenter_key" {
  description = "Canonical Ansible Vault vCenter key selected by the runner."
  type        = string
  default     = null
  nullable    = true
}

variable "datacenter" {
  description = "vSphere datacenter name; defaults from the selected Ansible Vault entry."
  type        = string
}

variable "template_folder" {
  description = "Optional vSphere inventory folder containing the source template."
  type        = string
  default     = null
  nullable    = true
}

variable "resource_pool" {
  description = "Optional named vSphere resource pool or inventory path; defaults to the selected host's root pool."
  type        = string
  default     = null
  nullable    = true
}

variable "compute_host" {
  description = "Optional vSphere host to select when using its root resource pool; omit only when the datacenter has one host."
  type        = string
  default     = null
  nullable    = true
}

variable "datastore" {
  description = "Destination datastore name."
  type        = string
}

variable "network" {
  description = "Destination vSphere network or port group name."
  type        = string
}

variable "vm_name" {
  description = "Virtual machine inventory name. Defaults to the catalog logical image name."
  type        = string
  default     = null
  nullable    = true
}

variable "vm_folder" {
  description = "Optional VM folder path relative to the datacenter VM folder."
  type        = string
  default     = null
  nullable    = true
}

variable "num_cpus" {
  description = "Number of virtual CPUs."
  type        = number
  default     = 2
}

variable "memory_mb" {
  description = "Virtual machine memory in megabytes."
  type        = number
  default     = 4096
}

variable "disk_size_gb" {
  description = "Boot disk size in GB; must be at least the source template disk size."
  type        = number
  default     = 35
}

variable "thin_provisioned" {
  description = "Provision the cloned boot disk as thin, when supported by the datastore."
  type        = bool
  default     = true
}

variable "guest_id" {
  description = "Optional VMware guest OS identifier override; defaults to the source template's guest ID."
  type        = string
  default     = null
  nullable    = true
}

variable "scsi_type" {
  description = "Virtual SCSI controller type; match the controller used by the source template."
  type        = string
  default     = "lsilogic"
}

variable "ssh_public_key" {
  description = "Optional OpenSSH public key passed to cloud-init through VMware GuestInfo metadata."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition     = var.ssh_public_key == null || length(trimspace(var.ssh_public_key)) > 0
    error_message = "ssh_public_key must be a non-empty OpenSSH public key when set."
  }
}
