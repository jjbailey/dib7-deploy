# GCP Instance Environment

This Terraform root launches one Compute Engine instance from a published
`compute_image` entry selected by `bin/generate-gcp-tfvars.py`. The generated
tfvars identify the shared catalog image. Destination project, zone, network,
SSH public key, and machine settings belong in a separate local launch
settings file under `inventory/gcp/`.

The catalog's `image_project` identifies the image owner. By default, the
deployment project comes from `gcp_project` in the selected Ansible Vault
entry; set `project_id` in local launch settings to override it. The deployment
service account must have permission to use the shared image in its source
project and create instances in the destination project.

Use [`bin/terraform-gcp.py`](../../bin/terraform-gcp.py) for plans and applies.
It reads the service-account key from Vault and passes it through the
environment. See [`doc/vault-gcp.md`](../../doc/vault-gcp.md) for Vault setup
and the full launch example.

Terraform stores local state at `inventory/gcp/terraform.tfstate`. State is
ignored by Git; keep it local and back it up to a secured location outside the
repository.
See [`doc/state-management.md`](../../doc/state-management.md) for named
workspaces and external state backups.
