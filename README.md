# dib7-deploy

Terraform project for launching instances from images published by
[dib7](../dib7). `dib7` remains responsible for building QCOW2
images, importing them into supported clouds, and publishing their artifact
identifiers to its image catalog.

The initial provider scope is AWS, GCP, OpenStack, and VMware vSphere. Terraform
will read the catalog contract documented in
[`dib7/doc/image-catalog.md`](../dib7/doc/image-catalog.md), then use a
selected published image to launch an instance in the corresponding
environment.

## Repository layout

- `inventory/` holds generated or machine-specific deployment data locally.
  Reviewed catalog tfvars and launch settings are tracked in the private
  checkout; Terraform state, backups, plans, and provider caches are not.
  `local/rsync-to-dib7-deploy.sh` excludes inventory from the public checkout.
- Terraform source, reusable modules, and committed examples belong in the
  normal source folders, separate from generated inventory.

The catalog is the source for published image identifiers. Generated tfvars are
reproducible, but review launch settings before committing them. Keep Terraform
state backed up separately; state can contain sensitive resource attributes.

## Generate provider tfvars

The scripts in `bin/` select a published image from the dib7 catalog and
write catalog-derived tfvars under `inventory/<provider>/`. The `--project`,
`--region`, and `--scope` options select catalog rows; wrapper target selectors
choose credentials from Vault. Set the shell variable `AWS_TARGET_PROJECT` to
your target AWS account ID, then run:

```bash
: "${AWS_TARGET_PROJECT:?Set the target AWS account ID}"
python3 bin/generate-aws-tfvars.py ubuntu26041-base --region us-west-2 --project "${AWS_CATALOG_PROJECT:-$AWS_TARGET_PROJECT}"
```

See [`bin/README.md`](bin/README.md) for all provider commands and scope
selectors.

The launch environments are [AWS](environments/aws/README.md),
[GCP](environments/gcp/README.md), [OpenStack](environments/openstack/README.md),
and [vSphere](environments/vsphere/README.md). Each uses catalog-derived image
fields and keeps destination placement and VM settings in local inventory.
Provider credentials are read from HashiCorp Vault at runtime; Vault mirrors
the provider data in `dib7` Ansible Vault, which remains the source of
truth. See [`doc/vault-sync.md`](doc/vault-sync.md),
[`doc/vault-aws.md`](doc/vault-aws.md),
[`doc/vault-gcp.md`](doc/vault-gcp.md),
[`doc/vault-openstack.md`](doc/vault-openstack.md), and
[`doc/vault-vsphere.md`](doc/vault-vsphere.md).

## Checks

Run the catalog and Vault-runner unit tests with:

```bash
python3 -m unittest discover -s tests -v
```

This repository currently has no tracked CI pipeline; run the unit tests and
Terraform formatting check locally before committing:

```bash
terraform fmt -check -recursive environments/
```

See [`doc/state-management.md`](doc/state-management.md) for separate
deployment workspaces and state backups.

The scripts in [`local/`](local/README.md) are manual smoke tests that create
real cloud resources; they are separate from the unit tests.
