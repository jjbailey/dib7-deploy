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

  tags = merge(var.tags, {
    Name = var.instance_name == null ? var.image_logical_name : var.instance_name
  })
}
