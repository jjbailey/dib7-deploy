# Azure Instance Environment

This Terraform root launches one Linux VM from a published `managed_image`
entry selected by `bin/generate-azure-tfvars.py`. The generated tfvars
identify the catalog image. Destination resource group, subnet, network
security group, SSH key, and VM settings belong in a separate local launch
settings file under `inventory/azure/`.

The catalog's `image_project` is the subscription that holds the managed
image, and the VM is created in the image's location (`image_region`): a
managed image can only be used in its own region. By default, the deployment
resource group comes from `resource_group` in the selected Ansible Vault
entry; set `resource_group_name` in local launch settings to override it. The
subnet, and any network security group, must already exist. The root creates
the VM's network interface and, unless `assign_public_ip` is `false`, a static
Standard public IP address.

## Select a published image

From the repository root, browse published Azure entries and generate tfvars
for the subscription that holds the image:

```bash
python3 ../dib7/bin/list-image-catalog.py \
  --provider azure --image ubuntu26041-base
: "${AZURE_CATALOG_PROJECT:?Set the catalog image subscription ID}"
python3 bin/generate-azure-tfvars.py ubuntu26041-base \
  --project "$AZURE_CATALOG_PROJECT"
```

Use the subscription shown in the catalog report. The generator writes
`inventory/azure/ubuntu26041-base-project-${AZURE_CATALOG_PROJECT}-resource_group-<resource-group>.tfvars`.
When the image is published in more than one location or resource group, add
`--region` and/or `--scope resource_group=<resource-group>` to select one.
See [`doc/vault-azure.md`](../../doc/vault-azure.md) for network
prerequisites, launch settings, and plan/apply commands.

Use [`bin/terraform-azure.py`](../../bin/terraform-azure.py) for plans and
applies. It reads the service principal from Vault and passes it through the
environment. See [`doc/vault-azure.md`](../../doc/vault-azure.md) for Vault
setup and the full launch example.

Terraform stores local state at `inventory/azure/terraform.tfstate` (default
workspace; named workspaces use
`inventory/azure/terraform.tfstate.d/<workspace>/terraform.tfstate`). State is
ignored by Git; keep it local and back it up to a secured location outside the
repository.
See [`doc/state-management.md`](../../doc/state-management.md) for named
workspaces and external state backups.
