# vSphere Instance Environment

This Terraform root clones a published vSphere inventory template selected
from the dib7 image catalog. dib7 imports the OVA into a Content
Library item named after the image, then creates a separate vSphere inventory
template whose name is recorded as the catalog `artifact_id` (for example,
`ubuntu26041-base.tmpl`). Terraform looks up and clones that inventory
template. Catalog scope identifies the vCenter and content library.
Datacenter, compute host, datastore, network, and VM sizing are launch settings
kept separately under `inventory/vsphere/`. If no named resource pool is
specified, Terraform uses the selected host's implicit root resource pool; set
`compute_host` when the datacenter has multiple hosts. The new VM inherits its
VMware guest ID from the source template unless `guest_id` is explicitly
overridden. Set `disk_size_gb` to at least the source template's first disk
size; the vSphere clone operation rejects a smaller destination disk.

Run plans and applies with [`bin/terraform-vsphere.py`](../../bin/terraform-vsphere.py).
The wrapper selects vCenter credentials from HashiCorp Vault and passes them
to the provider through its process environment. HashiCorp Vault mirrors
`dib7/vaults/vsphere.yml`; that Ansible Vault file is the source of truth.
See [`doc/vault-vsphere.md`](../../doc/vault-vsphere.md) for Vault setup,
catalog generation, and a launch example.

Terraform state is local at `inventory/vsphere/terraform.tfstate`. The private
checkout tracks inventory for development; protect and back it up separately.
See [`doc/state-management.md`](../../doc/state-management.md) for named
workspaces and external state backups.
