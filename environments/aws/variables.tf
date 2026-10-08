variable "image_logical_name" {
  description = "Logical image name selected from the dib7 catalog."
  type        = string
}

variable "image_artifact_id" {
  description = "AMI ID selected from the dib7 catalog."
  type        = string

  validation {
    condition     = can(regex("^ami-[0-9a-f]+$", var.image_artifact_id))
    error_message = "image_artifact_id must be an AWS AMI ID."
  }
}

variable "image_artifact_type" {
  description = "Catalog artifact type; AWS deployments require ami."
  type        = string

  validation {
    condition     = var.image_artifact_type == "ami"
    error_message = "image_artifact_type must be ami for AWS."
  }
}

variable "image_version" {
  description = "Catalog version selected by the AWS tfvars generator."
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
  description = "AWS account recorded as the catalog image owner."
  type        = string
  default     = null
  nullable    = true
}

variable "image_region" {
  description = "AWS region containing the selected catalog AMI."
  type        = string

  validation {
    condition     = length(trimspace(var.image_region)) > 0
    error_message = "image_region must be set by the AWS catalog entry."
  }
}

variable "image_scope" {
  description = "Additional scope metadata recorded for the catalog image."
  type        = map(string)
  default     = {}
}

variable "instance_name" {
  description = "EC2 Name tag. Defaults to the catalog logical image name."
  type        = string
  default     = null
  nullable    = true
}

variable "instance_type" {
  description = "EC2 instance type. Confirm the type is available in the selected region and supports the image architecture."
  type        = string
  default     = "t3.small"
}

variable "subnet_id" {
  description = "Optional VPC subnet. When omitted, AWS uses its default network selection."
  type        = string
  default     = null
  nullable    = true
}

variable "vpc_security_group_ids" {
  description = "VPC security groups to attach to the instance."
  type        = list(string)
  default     = null
  nullable    = true
}

variable "key_name" {
  description = "Optional existing EC2 key pair name for SSH access."
  type        = string
  default     = null
  nullable    = true
}

variable "associate_public_ip_address" {
  description = "Optional public IPv4 assignment override for the network interface."
  type        = bool
  default     = null
  nullable    = true
}

variable "iam_instance_profile" {
  description = "Optional existing IAM instance profile name."
  type        = string
  default     = null
  nullable    = true
}

variable "tags" {
  description = "Additional EC2 instance tags."
  type        = map(string)
  default     = {}
}
