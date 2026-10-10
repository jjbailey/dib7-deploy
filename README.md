# dib7-deploy

Terraform project for launching instances from images published by
[`dib7`](https://github.com/jjbailey/dib7). `dib7` remains responsible for
building QCOW2 images, importing them into supported clouds, and publishing
their artifact identifiers to its image catalog.

This project supports AWS, GCP, OpenStack, and VMware vSphere. The tfvars
generators read the catalog contract documented in
[`doc/image-catalog.md`](https://github.com/jjbailey/dib7/blob/main/doc/image-catalog.md),
and each provider's Terraform root uses the selected published image to launch
an instance in the corresponding environment.

## Prerequisites

- Terraform 1.5.0 or later (the provider roots require `>= 1.5.0`).
- Python 3 with the dependencies in `requirements.txt` (`boto3` for the AWS
  wrapper, `PyYAML` for the Vault sync script). The docs install them into
  `~/.dib7` with `~/.dib7/bin/python -m pip install -r requirements.txt`.
- The HashiCorp `vault` CLI, configured as described in
  [`doc/vault-sync.md`](doc/vault-sync.md), and `ansible-vault` for syncing.
- A sibling `dib7` checkout, which supplies the image catalog and the
  encrypted provider vaults.

## Repository layout

- `bin/` holds the catalog-to-tfvars generators, the Vault-backed Terraform
  wrappers, and the Vault sync and state backup scripts. See
  [`bin/README.md`](bin/README.md).
- `environments/` holds one Terraform root per provider: `aws`, `gcp`,
  `openstack`, and `vsphere`.
- `doc/` holds the Vault and state-management guides.
- `policies/` holds the HashiCorp Vault policies for the wrappers and the sync
  command.
- `inventory/` holds generated or machine-specific deployment data locally.
  Reviewed catalog tfvars and launch settings are tracked in the private
  checkout; Terraform state, backups, plans, and provider caches are not.
  `local/rsync-to-dib7-deploy.sh` excludes inventory from the public checkout.
  See [`inventory/README.md`](inventory/README.md).
- `local/` holds the private export script and manual cloud smoke tests. See
  [`local/README.md`](local/README.md).
- `tests/` holds the unit tests.

The catalog is the source for published image identifiers. Generated tfvars are
reproducible, but review launch settings before committing them. Keep Terraform
state backed up separately; state can contain sensitive resource attributes.

## Browse and deploy a published image

From the repository root, list all published catalog entries:

```bash
python3 ../dib7/bin/list-image-catalog.py
```

Filter the report to find a logical image in a provider, for example:

```bash
python3 ../dib7/bin/list-image-catalog.py \
  --provider openstack --image ubuntu26041-base
```

Choose the entry whose provider, project, region, and scope match the target
environment. The report includes its version and artifact ID. Each provider's
tfvars generator selects the newest published entry for the image and scope;
review the generated `image_version` and `image_artifact_id` before planning.
The provider READMEs show the catalog lookup and generator command, while the
Vault guides cover credentials, launch settings, and plan/apply commands.

See [`bin/README.md`](bin/README.md) for generator selectors and
[`doc/state-management.md`](doc/state-management.md) for separate Terraform
workspaces.

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
