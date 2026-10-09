# Vault credentials for GCP Terraform

The GCP Terraform wrapper selects a project entry from HashiCorp Vault KV v2
and supplies its service-account key to the Google provider through the
Terraform process environment. HashiCorp Vault mirrors
`dib7/vaults/gcp.yml`; that Ansible Vault file is the source of truth. See
[`vault-sync.md`](vault-sync.md) for the sync command. The key is not written
to tfvars, a temporary file, a Terraform data resource, or Terraform state.
The wrapper also removes Vault and OpenBao tokens and alternate Google
Application Default Credentials sources from Terraform's environment.

## Prerequisites

- A HashiCorp Vault server with TLS configured and trusted by this host.
- `VAULT_ADDR` and a non-root `VAULT_TOKEN` that can read the selected KV v2
  path. The Vault CLI may also obtain a token from its configured token helper.
- The `vault` CLI, Terraform, and Python 3.
- A GCP service-account key JSON in the selected project entry in
  `dib7/vaults/gcp.yml`. The sync command mirrors this data into KV v2.
  Grant the service account only the permissions needed to create instances
  in the selected project.
- The Compute Engine API must already be enabled. Grant
  `roles/iam.serviceAccountUser` as well if Terraform attaches a service
  account to the instance.

Create a dedicated Vault policy:

```bash
vault policy write dib7-deploy-gcp-read policies/dib7-deploy-gcp-read.hcl
```

The policy permits reading `dib7-deploy/gcp` from the `secret` mount and grants
no write or delete access. The sync command writes the complete `gcp_projects`
mapping, including each `service_account_key`, to
`secret/dib7-deploy/gcp`. Set `DIB7_VAULT_GCP_SECRET_PATH` or
`DIB7_VAULT_KV_MOUNT` to use another location.

## Generate catalog variables and launch

Generate the image variables from the current `dib7` catalog. The
catalog's `image_project` identifies the project that owns the shared image;
the selected Ansible Vault entry's `gcp_project` supplies Terraform's default
deployment project. Set `GCP_TARGET_PROJECT` to the deployment project ID and
`GCP_CATALOG_PROJECT` to the catalog image owner's project ID before running
the examples. They can be the same. These are shell variables used to build
the generator and file paths; the Terraform wrapper's Vault selector is
`DIB7_GCP_TARGET_PROJECT` or `--target-project`. Set `project_id` in the local
settings file only when you want to deploy to a different project.

```bash
python3 bin/generate-gcp-tfvars.py ubuntu26041-base --project "${GCP_CATALOG_PROJECT}"
```

Create a local launch settings file such as
`inventory/gcp/ubuntu26041-base-launch.settings.tfvars`:

```hcl
zone             = "us-west1-b"
instance_name    = "ubuntu26041-test"
machine_type      = "e2-medium"
network           = "default"
assign_public_ip = true

# Optional override; defaults to gcp_project from the selected Ansible Vault entry.
# project_id = "another-deployment-project"

# Optional: paste the public key line only. The SSH username comes from the
# selected catalog entry (for Ubuntu, usually "ubuntu").
ssh_public_key = "ssh-ed25519 AAAA... workstation"
```

Initialize and plan from the repository root:

```bash
terraform -chdir=environments/gcp init
python3 bin/terraform-gcp.py plan \
  -var-file="../../inventory/gcp/ubuntu26041-base-project-${GCP_CATALOG_PROJECT}.tfvars" \
  -var-file=../../inventory/gcp/ubuntu26041-base-launch.settings.tfvars
```

If the Ansible Vault contains multiple GCP entries, select the same key or
project ID with the wrapper's `--target-project` option before the Terraform
command, or set
`DIB7_GCP_TARGET_PROJECT`:

```bash
python3 bin/terraform-gcp.py --target-project "${GCP_TARGET_PROJECT}" plan \
  -var-file="../../inventory/gcp/ubuntu26041-base-project-${GCP_CATALOG_PROJECT}.tfvars" \
  -var-file=../../inventory/gcp/ubuntu26041-base-launch.settings.tfvars
```

Use `python3 bin/terraform-gcp.py apply` with the same variable files to
launch. `assign_public_ip` allocates an external address; VPC firewall rules
must still allow SSH from an appropriate source range. If you provide
`ssh_public_key`, Terraform combines it with `image_ssh_username` from the
catalog and installs that key through instance metadata. You can instead use
OS Login or keys already managed by the project and leave `ssh_public_key`
unset.

Terraform state is local and plaintext at `inventory/gcp/terraform.tfstate`.
It records the instance and its metadata, but not the service-account key used
to authenticate the provider. State is ignored by Git; protect it and back it
up outside the repository. Plans and applies fetch the key anew from Vault; `init`, `fmt`,
`validate`, and Terraform `state` commands do not require it.
