# OpenStack Terraform setup

The OpenStack runner reads the selected project from HashiCorp Vault KV v2,
then passes authentication settings to the provider through its supported
`OS_*` environment variables. The encrypted
`dib7/vaults/openstack.yml` is the source of truth; HashiCorp Vault is its
runtime mirror. Passwords are not put in tfvars or Terraform resource
configuration.

## Vault setup

Mirror the Ansible Vault source after it changes:

```bash
~/.dib7/bin/python bin/sync-ansible-vault-to-hashicorp.py openstack
```

The source supports an `openstack_projects` mapping and the legacy
`openstack_auth` mapping. With no explicit selector, the legacy mapping takes
precedence when both are present, matching dib7. Otherwise a single
project entry is selected automatically. For multiple projects, select a
Vault key, project name, or project ID with `--target-project` before the
Terraform command, or set `DIB7_OPENSTACK_TARGET_PROJECT`.

Create the runner's read policy and the sync policy:

```bash
vault policy write dib7-deploy-openstack-read policies/dib7-deploy-openstack-read.hcl
vault policy write dib7-deploy-vault-sync policies/dib7-deploy-vault-sync.hcl
```

The OpenStack provider receives authentication through `OS_AUTH_URL`,
`OS_USERNAME`, `OS_PASSWORD`, and either `OS_PROJECT_ID` or `OS_PROJECT_NAME`,
plus optional domain and region variables. When Vault supplies a project ID,
the runner prefers it and omits the project name. It clears inherited
OpenStack authentication variables before setting the selected Vault values,
so another sourced OpenStack environment cannot silently change the target.

## Generate catalog variables and launch

Generate tfvars from the current `glance_image` catalog row. Select the same
project and region recorded in the catalog. Set `OS_CATALOG_PROJECT` to that
catalog project before running the generation example. Set
`OS_TARGET_PROJECT` separately to the project where Terraform will create the
server; it may differ when the image is shared. These are shell variables for
the catalog path and generator arguments. The Vault entry is selected by
`DIB7_OPENSTACK_TARGET_PROJECT` or `--target-project`:

```bash
python3 bin/generate-openstack-tfvars.py ubuntu26041-base \
  --project ${OS_CATALOG_PROJECT} \
  --region US-WEST-OR-1
```

This writes
`inventory/openstack/ubuntu26041-base-project-${OS_CATALOG_PROJECT}.tfvars`.
The catalog project identifies the image owner. Terraform creates the server
in the project selected from Vault; that can be a different project if the
image is shared with it.

Create a separate local launch settings file such as
`inventory/openstack/ubuntu26041-base-launch.settings.tfvars`:

```hcl
instance_name = "ubuntu26041-test"
flavor_name   = "REPLACE_WITH_FLAVOR"
network_name  = "REPLACE_WITH_NETWORK"

# Set network_id instead of network_name when selecting by UUID.
# network_id = "REPLACE_WITH_NETWORK_UUID"

# Defaults to the catalog SSH username; the matching key pair must exist
# in the selected OpenStack project.
# key_pair = "ubuntu"

security_groups = ["default"]
```

Set exactly one of `network_name` and `network_id`. The flavor and network
must exist in the selected project and region. The key pair defaults to the
catalog SSH username; set `key_pair` explicitly to use a differently named
existing Nova key pair. `security_groups` defaults to `default`.

Initialize and plan from the repository root:

```bash
python3 bin/terraform-openstack.py init
python3 bin/terraform-openstack.py plan \
  -var-file=../../inventory/openstack/ubuntu26041-base-project-${OS_CATALOG_PROJECT}.tfvars \
  -var-file=../../inventory/openstack/ubuntu26041-base-launch.settings.tfvars
```

For multiple Vault projects, choose the matching entry before the Terraform
command:

```bash
python3 bin/terraform-openstack.py --target-project ${OS_TARGET_PROJECT} plan \
  -var-file=../../inventory/openstack/ubuntu26041-base-project-${OS_CATALOG_PROJECT}.tfvars \
  -var-file=../../inventory/openstack/ubuntu26041-base-launch.settings.tfvars
```

Review the plan before applying. Terraform state is plaintext at
`inventory/openstack/terraform.tfstate`; it is ignored by Git. Protect it and
back it up outside the repository.
