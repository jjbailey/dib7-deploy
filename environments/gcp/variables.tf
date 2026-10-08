variable "image_logical_name" {
  description = "Logical image name selected from the dib7 catalog."
  type        = string
}

variable "image_artifact_id" {
  description = "Compute Engine image self-link selected from the catalog."
  type        = string

  validation {
    condition     = can(regex("^(https://www\\.googleapis\\.com/compute/v1/)?projects/[^/]+/global/images/[^/]+$", var.image_artifact_id))
    error_message = "image_artifact_id must identify a Compute Engine project image."
  }
}

variable "image_artifact_type" {
  description = "Catalog artifact type; GCP deployments require compute_image."
  type        = string

  validation {
    condition     = var.image_artifact_type == "compute_image"
    error_message = "image_artifact_type must be compute_image for GCP."
  }
}

variable "image_version" {
  description = "Catalog version selected by the GCP tfvars generator."
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
  description = "Default non-root SSH login recorded for the catalog image."
  type        = string
  default     = null
  nullable    = true
}

variable "image_project" {
  description = "GCP project recorded as the catalog image owner; separate from the deployment project."
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

variable "project_id" {
  description = "GCP project where the Compute Engine instance will be created."
  type        = string

  validation {
    condition     = length(trimspace(var.project_id)) > 0
    error_message = "project_id must name the GCP deployment project."
  }
}

variable "zone" {
  description = "Compute Engine zone for the instance, such as us-west1-b."
  type        = string

  validation {
    condition     = can(regex("^[a-z]+-[a-z]+[0-9]+-[a-z]$", var.zone))
    error_message = "zone must be a Compute Engine zone such as us-west1-b."
  }
}

variable "instance_name" {
  description = "Compute Engine instance name. Defaults to the catalog logical image name."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition     = var.instance_name == null || (length(var.instance_name) <= 63 && can(regex("^[a-z]([-a-z0-9]*[a-z0-9])?$", var.instance_name)))
    error_message = "instance_name must be a lowercase RFC1035 name of at most 63 characters."
  }
}

variable "machine_type" {
  description = "Compute Engine machine type available in the selected zone and compatible with the image architecture."
  type        = string
  default     = "e2-medium"
}

variable "network" {
  description = "VPC network name or self-link. Set to null when selecting only a subnetwork."
  type        = string
  default     = "default"
  nullable    = true
}

variable "subnetwork" {
  description = "Optional subnetwork name or self-link for custom VPC layouts."
  type        = string
  default     = null
  nullable    = true
}

variable "assign_public_ip" {
  description = "Whether to attach an ephemeral external IPv4 address. Firewall rules still control inbound access."
  type        = bool
  default     = true
}

variable "boot_disk_size_gb" {
  description = "Optional boot disk size; null inherits the source image size."
  type        = number
  default     = null
  nullable    = true
}

variable "boot_disk_type" {
  description = "Compute Engine boot disk type."
  type        = string
  default     = "pd-balanced"
}

variable "network_tags" {
  description = "Network tags used by VPC firewall rules targeting this instance."
  type        = list(string)
  default     = []
}

variable "ssh_public_key" {
  description = "Optional OpenSSH public key. The catalog SSH username is used in the instance ssh-keys metadata entry."
  type        = string
  default     = null
  nullable    = true
}

variable "metadata" {
  description = "Additional non-secret instance metadata. The ssh-keys entry is composed from ssh_public_key when set."
  type        = map(string)
  default     = {}
}

variable "labels" {
  description = "Additional GCP labels. Catalog provenance labels are added automatically."
  type        = map(string)
  default     = {}
}

variable "service_account_email" {
  description = "Optional service account to attach to the instance."
  type        = string
  default     = null
  nullable    = true
}

variable "service_account_scopes" {
  description = "OAuth scopes for an attached instance service account."
  type        = list(string)
  default     = ["https://www.googleapis.com/auth/cloud-platform"]
}

variable "allow_stopping_for_update" {
  description = "Allow Terraform to stop the instance for updates that require it, such as a machine type change."
  type        = bool
  default     = false
}
