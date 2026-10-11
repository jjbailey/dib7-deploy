# OpenStack Instance Environment

This Terraform root launches one Nova instance from a Glance image selected
from the dib7 catalog. The image UUID, project, and region come from the
catalog; flavor, network, key pair, security groups, and optional availability
zone are local launch settings.

The catalog's project identifies the project that owns the image. The project
used to create a server comes from the selected Vault credentials and may
differ when the image is shared with that project.

## Select a published image

From the repository root, browse published OpenStack entries and generate
tfvars using the image owner's project and catalog region:

```bash
python3 ../dib7/bin/list-image-catalog.py \
  --provider openstack --image ubuntu26041-base
: "${OS_CATALOG_PROJECT:?Set the catalog image owner project}"
: "${OS_CATALOG_REGION:?Set the catalog region from the report}"
python3 bin/generate-openstack-tfvars.py ubuntu26041-base \
  --project "$OS_CATALOG_PROJECT" --region "$OS_CATALOG_REGION"
```

The generator writes
`inventory/openstack/ubuntu26041-base-project-${OS_CATALOG_PROJECT}.tfvars`.
See [`doc/vault-openstack.md`](../../doc/vault-openstack.md) for launch
settings and plan/apply commands.

The OpenStack runner reads authentication from HashiCorp Vault and passes it to
the provider through `OS_*` environment variables. The encrypted
`dib7/vaults/openstack.yml` file remains the source of truth. See
[`doc/vault-openstack.md`](../../doc/vault-openstack.md) for Vault setup and a
plan example.

Terraform state is local at `inventory/openstack/terraform.tfstate` (default
workspace; named workspaces use
`inventory/openstack/terraform.tfstate.d/<workspace>/terraform.tfstate`) and
ignored by Git. Keep it local and back it up to a secured location outside the
repository.
See [`doc/state-management.md`](../../doc/state-management.md) for named
workspaces and external state backups.
