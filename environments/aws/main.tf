locals {
  # DIB7 images conventionally use an EC2 key pair named after the default
  # login. An explicit launch setting can override that account-side choice.
  effective_key_name = var.key_name != null ? var.key_name : var.image_ssh_username
}

resource "aws_instance" "image" {
  ami                         = var.image_artifact_id
  instance_type               = var.instance_type
  subnet_id                   = var.subnet_id
  vpc_security_group_ids      = var.vpc_security_group_ids
  key_name                    = local.effective_key_name
  associate_public_ip_address = var.associate_public_ip_address
  iam_instance_profile        = var.iam_instance_profile

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = var.metadata_http_tokens
  }

  tags = merge(var.tags, {
    Name = var.instance_name == null ? var.image_logical_name : var.instance_name
  })
}

# Old AMIs are deregistered outside Terraform, and aws_instance does not
# validate its AMI until apply. This reports a missing AMI during plan. It is a
# check rather than a precondition so an instance whose AMI was already pruned
# can still be planned and destroyed.
check "catalog_ami_available" {
  data "aws_ami_ids" "catalog" {
    owners             = [coalesce(var.image_project, "self")]
    include_deprecated = true

    filter {
      name   = "image-id"
      values = [var.image_artifact_id]
    }
  }

  assert {
    condition     = contains(data.aws_ami_ids.catalog.ids, var.image_artifact_id)
    error_message = "AMI ${var.image_artifact_id} (catalog version ${var.image_version}) is not available to this account; it may have been deregistered. Regenerate the tfvars from the current catalog before creating or replacing the instance."
  }
}
