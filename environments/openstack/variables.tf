variable "image_logical_name" {
  description = "Logical image name selected from the dib7 catalog."
  type        = string
}

variable "image_artifact_id" {
  description = "Glance image UUID selected from the dib7 catalog."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-fA-F-]{36}$", var.image_artifact_id))
    error_message = "image_artifact_id must be a Glance image UUID."
  }
}

variable "image_artifact_type" {
  description = "Catalog artifact type; OpenStack deployments require glance_image."
  type        = string

  validation {
    condition     = var.image_artifact_type == "glance_image"
    error_message = "image_artifact_type must be glance_image for OpenStack."
  }
}

variable "image_version" {
  description = "Catalog version selected by the OpenStack tfvars generator."
  type        = string
}

variable "image_architecture" {
  description = "Architecture recorded for the catalog image."
  type        = string
}

variable "image_boot_mode" {
  description = "Boot mode recorded for the catalog image."
  type        = string
}

variable "image_ssh_username" {
  description = "Default non-root SSH login recorded for the catalog image."
  type        = string
  default     = null
  nullable    = true
}

variable "image_project" {
  description = "OpenStack project recorded as the catalog image owner."
  type        = string
  default     = null
  nullable    = true
}

variable "image_region" {
  description = "OpenStack region recorded for the catalog image."
  type        = string

  validation {
    condition     = length(trimspace(var.image_region)) > 0
    error_message = "image_region must be set by the OpenStack catalog entry."
  }
}

variable "target_region" {
  description = "Optional region from the selected Vault project, used to validate catalog scope."
  type        = string
  default     = null
  nullable    = true
}

variable "instance_name" {
  description = "OpenStack server name. Defaults to the catalog logical image name."
  type        = string
  default     = null
  nullable    = true
}

variable "flavor_name" {
  description = "Existing OpenStack flavor name for the new server."
  type        = string
}

variable "network_name" {
  description = "Existing Neutron network name; set exactly one of network_name or network_id."
  type        = string
  default     = null
  nullable    = true
}

variable "network_id" {
  description = "Existing Neutron network UUID; set exactly one of network_name or network_id."
  type        = string
  default     = null
  nullable    = true
}

variable "key_pair" {
  description = "Existing OpenStack key pair name. Defaults to the catalog SSH username."
  type        = string
  default     = null
  nullable    = true
}

variable "security_groups" {
  description = "Existing OpenStack security group names to attach to the server."
  type        = list(string)
  default     = ["default"]
}

variable "availability_zone" {
  description = "Optional OpenStack compute availability zone."
  type        = string
  default     = null
  nullable    = true
}

variable "metadata" {
  description = "Additional Nova server metadata."
  type        = map(string)
  default     = {}
}
