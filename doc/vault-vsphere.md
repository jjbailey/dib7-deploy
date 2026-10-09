# Vault credentials for vSphere Terraform

The vSphere runner reads HashiCorp Vault KV v2 and passes the selected
credentials to the Terraform provider through `VSPHERE_*` environment
variables. With no explicit selector, flat legacy credentials take precedence
when present, matching dib7; otherwise a single `vsphere_projects` entry
is selected automatically. `dib7/vaults/vsphere.yml` is the
source of truth; see [`vault-sync.md`](vault-sync.md) for how to mirror it.
The vCenter password is not placed in tfvars or Terraform state.

dib7 imports the OVA into a content library item named after the image,
then creates a separate vSphere inventory template (for example,
`ubuntu26041-base.tmpl`). The catalog's `artifact_id` names that inventory
template, which Terraform looks up and clones. See the [vSphere provider
documentation](https://registry.terraform.io/providers/vmware/vsphere/latest/docs)
for supported inventory resources and launch settings.

## Vault setup

The Ansible Vault entries contain `vcenter_hostname`, `vcenter_username`,
`vcenter_password`, optional `datacenter`, and optional `validate_certs`.
Terraform selects one entry automatically when only one vCenter is configured.
For multiple entries, choose an Ansible key or hostname with
`--target-vcenter`.

Create a read-only policy for the Terraform runner:

```bash
vault policy write dib7-deploy-vsphere-read policies/dib7-deploy-vsphere-read.hcl
```

The policy grants read access to `secret/dib7-deploy/vsphere`. Sync changes
from the encrypted source with:

```bash
~/.dib7/bin/python bin/sync-ansible-vault-to-hashicorp.py vsphere
```

The selected entry's `validate_certs` defaults to `true`. The provider will
verify the vCenter certificate unless the Ansible Vault entry explicitly sets
`validate_certs: false`.

## Generate catalog variables and launch

Generate tfvars from the published `content_library_template` row. The
vCenter and content library selectors must match the catalog scope:

```bash
python3 bin/generate-vsphere-tfvars.py ubuntu26041-base \
  --scope vcenter=legacy \
  --scope content_library=Content_Library
```

This writes
`inventory/vsphere/ubuntu26041-base-content_library-Content_Library-vcenter-legacy.tfvars`.
The catalog entry supplies the inventory template name, boot mode, and SSH
username. Create a separate local launch settings file, for example
`inventory/vsphere/ubuntu26041-base-launch.settings.tfvars`:

```hcl
vm_name       = "ubuntu26041-test"
datastore     = "datastore1"
network       = "VM Network"
num_cpus      = 2
memory_mb     = 4096
disk_size_gb  = 35

# Optional: with multiple hosts, choose the host whose root pool to use.
# Omit this when the datacenter has a single host.
# compute_host = "esxi-01.example.com"

# Optional: choose a named pool instead of the host's root pool.
# resource_pool = "Cluster/Resources/Builds"

# Optional. The public key is delivered through VMware GuestInfo metadata.
ssh_public_key = "ssh-ed25519 AAAA... workstation"

# Optional overrides for image or inventory defaults:
# vm_folder = "Workloads"
# template_folder = "Templates"
# guest_id  = "ubuntu64Guest" # defaults to the source template's guest ID
# scsi_type = "lsilogic"
```

The optional SSH key uses cloud-init's VMware GuestInfo datasource; the guest
image must have that datasource enabled and VMware Tools installed. The key is
installed for the guest image's default user, whose login name is recorded in
the catalog.

Initialize and plan from the repository root:

```bash
terraform -chdir=environments/vsphere init
python3 bin/terraform-vsphere.py plan \
  -var-file=../../inventory/vsphere/ubuntu26041-base-content_library-Content_Library-vcenter-legacy.tfvars \
  -var-file=../../inventory/vsphere/ubuntu26041-base-launch.settings.tfvars
```

When the Ansible Vault contains multiple vCenters, select the same key or
hostname used in the catalog scope:

```bash
python3 bin/terraform-vsphere.py --target-vcenter legacy plan \
  -var-file=../../inventory/vsphere/ubuntu26041-base-content_library-Content_Library-vcenter-legacy.tfvars \
  -var-file=../../inventory/vsphere/ubuntu26041-base-launch.settings.tfvars
```

Review the plan before `apply`. Terraform state is local plaintext at
`inventory/vsphere/terraform.tfstate`; it contains VM configuration and any
public key supplied through GuestInfo, but not the vCenter password. State is
ignored by Git; protect it and back it up outside the repository.

The vSphere provider can also be configured with `VSPHERE_SERVER`,
`VSPHERE_USER`, `VSPHERE_PASSWORD`, and
`VSPHERE_ALLOW_UNVERIFIED_SSL`; the wrapper sets these from the selected Vault
entry for plans and applies.
