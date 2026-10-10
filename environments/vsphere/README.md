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

## Select a published image

From the repository root, browse published vSphere entries. Use the vCenter
and content library values shown under `Scope` to generate the matching file:

```bash
python3 ../dib7/bin/list-image-catalog.py \
  --provider vsphere --artifact-type content_library_template \
  --image ubuntu26041-base
python3 bin/generate-vsphere-tfvars.py ubuntu26041-base \
  --scope vcenter=legacy --scope content_library=Content_Library
```

The generator writes the catalog-derived variables under
`inventory/vsphere/`.
See [`doc/vault-vsphere.md`](../../doc/vault-vsphere.md) for launch settings
and plan/apply commands.

Run plans and applies with [`bin/terraform-vsphere.py`](../../bin/terraform-vsphere.py).
The wrapper selects vCenter credentials from HashiCorp Vault and passes them
to the provider through its process environment. HashiCorp Vault mirrors
`dib7/vaults/vsphere.yml`; that Ansible Vault file is the source of truth.
See [`doc/vault-vsphere.md`](../../doc/vault-vsphere.md) for Vault setup,
catalog generation, and a launch example.

Terraform state is local at `inventory/vsphere/terraform.tfstate` (default
workspace; named workspaces use
`inventory/vsphere/terraform.tfstate.d/<workspace>/terraform.tfstate`) and
ignored by Git. Keep it local and back it up to a secured location outside the
repository.
See [`doc/state-management.md`](../../doc/state-management.md) for named
workspaces and external state backups.
