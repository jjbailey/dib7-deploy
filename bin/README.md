# Catalog to tfvars generators

Each provider script selects the latest `published` catalog row for a logical
image and writes a tfvars file under the private top-level `inventory/`
directory. AWS selects the newest numeric `version` in the selected catalog
scope. GCP, OpenStack, and vSphere normally have one current row per image and
scope; all providers fail if multiple projects, regions, or scopes match until
selectors are supplied. The selector values below are shell variables that
you set for the catalog owner/location. The generators require explicit
`--project` values where shown; they do not read the wrapper's `DIB7_*`
selectors. Catalog owner/project can differ from the deployment target.

```bash
: "${AWS_TARGET_PROJECT:?Set the target AWS account ID}"
: "${GCP_TARGET_PROJECT:?Set the GCP deployment project ID}"
: "${OS_CATALOG_PROJECT:?Set the OpenStack catalog owner project}"
python3 bin/generate-aws-tfvars.py ubuntu26041-base --region us-west-2 --project "${AWS_CATALOG_PROJECT:-$AWS_TARGET_PROJECT}"
python3 bin/generate-gcp-tfvars.py ubuntu26041-base --project "${GCP_CATALOG_PROJECT:-$GCP_TARGET_PROJECT}"
python3 bin/generate-openstack-tfvars.py ubuntu26041-base --region US-WEST-OR-1 --project "${OS_CATALOG_PROJECT}"
python3 bin/generate-vsphere-tfvars.py ubuntu26041-base --scope vcenter=legacy --scope content_library=Content_Library
```

The default catalog is `../dib7/catalogs/image-catalog.json`, resolved
relative to this repository. Pass `--catalog PATH` when consuming another
catalog snapshot. Use `--output PATH` to choose a different destination. By
default the output filename includes the selected project and non-location
scope, but omits region and zone for a consistent naming convention across
providers. All non-location scope values use the same `key-value` filename
format, including vSphere's vCenter and content-library scope. Use `--output`
to keep separate files for regional variants.

All generators emit the same catalog-derived variable names: `image_logical_name`,
`image_artifact_id`, `image_artifact_type`, `image_version`,
`image_architecture`, `image_boot_mode`, `image_ssh_username`, `image_project`,
`image_region`, and `image_scope`. The image's SSH username comes from the
catalog; account-specific networking remains in launch settings. AWS defaults
the EC2 key pair name to the SSH username when no explicit `key_name` is given.
OpenStack defaults the Nova key pair name to the catalog SSH username unless
`key_pair` is set explicitly.

The canonical provider settings and credentials remain in the encrypted
`dib7/vaults/` files. Mirror those files into HashiCorp Vault after
updating them with `bin/sync-ansible-vault-to-hashicorp.py`; see
`doc/vault-sync.md`.

The Terraform roots currently include AWS, GCP, OpenStack, and vSphere. Run
them with `bin/terraform-aws.py`, `bin/terraform-gcp.py`,
`bin/terraform-openstack.py`, and `bin/terraform-vsphere.py`; these wrappers
fetch provider credentials from Vault. See the provider environment READMEs
and `doc/vault-aws.md`, `doc/vault-gcp.md`, `doc/vault-openstack.md`, and
`doc/vault-vsphere.md` for launch inputs and Vault setup.

Use `python3 bin/backup-terraform-state.py DESTINATION` to copy state snapshots
to a mounted backup disk or secured share outside the repository. See
`doc/state-management.md` for backup and workspace details.
