# Vault credentials for Azure Terraform

The Azure Terraform wrapper selects a project entry from HashiCorp Vault KV v2
and supplies its service principal to the `azurerm` provider through the
Terraform process environment (`ARM_TENANT_ID`, `ARM_SUBSCRIPTION_ID`,
`ARM_CLIENT_ID`, and `ARM_CLIENT_SECRET`). HashiCorp Vault mirrors
`dib7/vaults/azure.yml`; that Ansible Vault file is the source of truth.
See [`vault-sync.md`](vault-sync.md) for the sync command. The secret is not
written to tfvars, a temporary file, a Terraform data resource, or Terraform
state. The wrapper also removes Vault and OpenBao tokens and alternate
`azurerm` credential sources (client certificates, OIDC tokens) from
Terraform's environment, and sets `ARM_USE_CLI=false` and `ARM_USE_MSI=false`
so a logged-in `az` session or a managed identity is never used instead.

## Prerequisites

- A HashiCorp Vault server with TLS configured and trusted by this host.
- `VAULT_ADDR` and a non-root `VAULT_TOKEN` that can read the selected KV v2
  path. The Vault CLI may also obtain a token from its configured token helper.
- The `vault` CLI, Terraform, and Python 3.
- An `azure_projects` entry in `dib7/vaults/azure.yml` with `tenant_id`,
  `subscription_id`, `client_id`, and `client_secret`. The entry's
  `resource_group` is Terraform's default deployment resource group. The sync
  command mirrors this data into KV v2. dib7's own import fields
  (`location`, `storage_account`, `storage_container`) are ignored here.
- The service principal needs permission to create network interfaces, public
  IP addresses, and VMs in the deployment resource group and to read the
  managed image (for example, Contributor on the resource group or the
  subscription).
- The `Microsoft.Compute` and `Microsoft.Network` resource providers must
  already be registered in the subscription. The Terraform root does not
  register providers. Check and register them once with:

  ```bash
  az provider show --namespace Microsoft.Compute --query registrationState
  az provider register --namespace Microsoft.Compute
  az provider register --namespace Microsoft.Network
  ```

Create a dedicated Vault policy:

```bash
vault policy write dib7-deploy-azure-read policies/dib7-deploy-azure-read.hcl
```

The policy permits reading `dib7-deploy/azure` from the `secret` mount and
grants no write or delete access. The sync command writes the complete
`azure_projects` mapping, including each `client_secret`, to
`secret/dib7-deploy/azure`. Set `DIB7_VAULT_AZURE_SECRET_PATH` or
`DIB7_VAULT_KV_MOUNT` to use another location.
Attach this read policy to the Vault identity or auth role used by the
Terraform operator. The identity used to sync credentials needs the separate
`dib7-deploy-vault-sync` policy; see [`vault-sync.md`](vault-sync.md).

## Network and SSH key

Azure has no default network. The Terraform root creates the VM, its network
interface, and (optionally) a public IP address, but it attaches them to an
existing subnet and, optionally, an existing network security group. Create
them once per location, for example:

```bash
az network vnet create --resource-group rg-wus2 --location westus2 \
  --name vnet-wus2 --address-prefixes 10.20.0.0/16 \
  --subnet-name default --subnet-prefixes 10.20.0.0/24
az network nsg create --resource-group rg-wus2 --location westus2 --name nsg-wus2
az network nsg rule create --resource-group rg-wus2 --nsg-name nsg-wus2 \
  --name allow-ssh --priority 1000 --direction Inbound --access Allow \
  --protocol Tcp --destination-port-ranges 22 --source-address-prefixes "$MY_IP"
```

A Standard public IP address denies all inbound traffic unless a network
security group allows it, so attach one with an SSH rule when you need to log
in. Restrict `--source-address-prefixes` to the addresses you connect from.

The VM's admin user is the catalog's `image_ssh_username`. Its SSH public key
comes from an Azure SSH public key resource, named after that username unless
`key_name` is set, in the deployment resource group unless
`key_resource_group_name` is set. Alternatively set `ssh_public_key` to the
public key line itself. Azure requires an SSH key; password login is disabled.

DIB7 images provision through cloud-init and do not include the Azure Linux
agent, so the VM is created with `provision_vm_agent = false` and VM
extensions are unavailable.

## Generate catalog variables and launch

Generate the image variables from the current `dib7` catalog. The
catalog's `image_project` is the subscription that holds the managed image,
and the VM is created in the image's location: a managed image can only be
used in its own region. Set `AZURE_CATALOG_PROJECT` to that subscription ID
before running the examples, and `AZURE_TARGET_PROJECT` to the Ansible Vault
key or subscription ID of the deployment entry. These are shell variables used
to build the generator and file paths; the Terraform wrapper's Vault selector
is `DIB7_AZURE_TARGET_PROJECT` or `--target-project`.

```bash
python3 bin/generate-azure-tfvars.py ubuntu26041-base --project "${AZURE_CATALOG_PROJECT}"
```

The generator writes
`inventory/azure/ubuntu26041-base-project-${AZURE_CATALOG_PROJECT}-resource_group-<resource-group>.tfvars`.
If the subscription publishes the image in more than one location or resource
group, the generator lists the matches and stops; add `--region <location>`
and/or `--scope resource_group=<resource-group>` to pick one.
Create a local launch settings file such as
`inventory/azure/ubuntu26041-base-launch.settings.tfvars`:

```hcl
instance_name             = "ubuntu26041-test"
vm_size                   = "Standard_B2als_v2"
subnet_id                 = "/subscriptions/<subscription-id>/resourceGroups/rg-wus2/providers/Microsoft.Network/virtualNetworks/vnet-wus2/subnets/default"
network_security_group_id = "/subscriptions/<subscription-id>/resourceGroups/rg-wus2/providers/Microsoft.Network/networkSecurityGroups/nsg-wus2"
assign_public_ip          = true
key_name                  = "cloud"

# Optional override; defaults to resource_group from the selected Ansible Vault entry.
# resource_group_name = "another-resource-group"
```

Other optional launch settings, with their defaults, are `zone` (none),
`key_resource_group_name` (the deployment resource group), `ssh_public_key`
(none), `os_disk_size_gb` (inherit the image size),
`os_disk_storage_account_type` (`StandardSSD_LRS`), `boot_diagnostics`
(`true`), and `tags` (`{}`). Check that the VM size is offered to your
subscription in the image's location and supports Hyper-V Gen2:

```bash
az vm list-skus --location westus2 --size Standard_B2 --output table
```

A size listed with zone restrictions can still be used with `zone` unset.

Initialize and plan from the repository root:

```bash
python3 bin/terraform-azure.py init
python3 bin/terraform-azure.py plan \
  -var-file="../../inventory/azure/ubuntu26041-base-project-${AZURE_CATALOG_PROJECT}-resource_group-rg-wus2.tfvars" \
  -var-file=../../inventory/azure/ubuntu26041-base-launch.settings.tfvars
```

If the Ansible Vault contains multiple Azure entries, select the key or
subscription ID with the wrapper's `--target-project` option before the
Terraform command, or set `DIB7_AZURE_TARGET_PROJECT`:

```bash
python3 bin/terraform-azure.py --target-project "${AZURE_TARGET_PROJECT}" plan \
  -var-file="../../inventory/azure/ubuntu26041-base-project-${AZURE_CATALOG_PROJECT}-resource_group-rg-wus2.tfvars" \
  -var-file=../../inventory/azure/ubuntu26041-base-launch.settings.tfvars
```

Use `python3 bin/terraform-azure.py apply` with the same variable files to
launch. dib7 supersedes Azure images in place, so the managed image's
resource ID stays the same across rebuilds; the root replaces the VM when the
catalog `image_version` changes.

Terraform state is local and plaintext at `inventory/azure/terraform.tfstate`
(or under `inventory/azure/terraform.tfstate.d/<workspace>/` for a named
workspace). It records the VM, its network resources, and the admin SSH
public key, but not the client secret used to authenticate the provider.
State is ignored by Git; protect it and back it up outside the repository.
Plans and applies fetch the secret anew from Vault; `init`, `fmt`,
`validate`, and Terraform `state` commands do not require it.
