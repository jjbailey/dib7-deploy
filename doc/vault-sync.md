# Keep HashiCorp Vault in sync with Ansible Vault

`dib7` owns the provider settings and credentials in its encrypted files:

- `dib7/vaults/aws.yml`
- `dib7/vaults/gcp.yml`
- `dib7/vaults/openstack.yml`
- `dib7/vaults/vsphere.yml`

Those Ansible Vault files are the source of truth. This repository mirrors each
complete provider document into HashiCorp Vault KV v2 so Terraform can read
credentials at runtime. Edit the Ansible Vault file first, then sync it:

```bash
~/.dib7/bin/python -m pip install -r requirements.txt
~/.dib7/bin/python bin/sync-ansible-vault-to-hashicorp.py aws
~/.dib7/bin/python bin/sync-ansible-vault-to-hashicorp.py gcp
~/.dib7/bin/python bin/sync-ansible-vault-to-hashicorp.py openstack
~/.dib7/bin/python bin/sync-ansible-vault-to-hashicorp.py vsphere
```

## Configure the Vault CLI on the client

This repository does not set Vault server or authentication environment
variables. The Terraform wrappers invoke `vault kv get`, passing the current
shell environment to the Vault CLI. Configure the endpoint in the shell where
you run the wrappers, such as in your shell profile or a private environment
file outside this repository:

```bash
export VAULT_ADDR="https://vault.example.com:8200"
# Optional when the Vault server uses a private certificate authority:
export VAULT_CACERT="$HOME/.config/vault/ca.pem"
```

Replace the example address and CA path with your Vault server's values. The
Vault CLI uses the system certificate store by default; `VAULT_CACERT` points
it to a PEM CA certificate when needed. Do not disable TLS verification for
normal use.

Authenticate with an auth method enabled by your Vault server, for example
`vault login` or `vault login -method=oidc`. The CLI's default token helper
caches the resulting token in `~/.vault-token`, so you usually do not need to
export `VAULT_TOKEN`. If you do provide `VAULT_TOKEN` for automation, supply it
through a secure runtime environment and never commit it to this repository.
The wrappers use that token for the Vault read, then remove it before starting
Terraform.

The `DIB7_VAULT_*` settings below configure KV mount and secret paths; they do
not configure the Vault server address or authentication.

The command uses `ansible-vault view`, following `VAULT_PASSWORD_FILE` or
`~/.ssh/dib-vault-pass` when available and prompting otherwise. It validates
the decrypted YAML, then streams it to the Vault CLI over stdin. It does not
print credential values or write decrypted data to a temporary file. Use
`--dry-run` to decrypt and validate without writing. The HashiCorp Vault token
used for sync needs `create` and `update` access to the four KV v2 data paths;
Terraform's provider runners use separate read-only policies.

By default, the exact Ansible mappings are mirrored here:

| Ansible source         | HashiCorp KV v2 path           |
| ---------------------- | ------------------------------ |
| `vaults/aws.yml`       | `secret/dib7-deploy/aws`       |
| `vaults/gcp.yml`       | `secret/dib7-deploy/gcp`       |
| `vaults/openstack.yml` | `secret/dib7-deploy/openstack` |
| `vaults/vsphere.yml`   | `secret/dib7-deploy/vsphere`   |

Override the KV mount with `--kv-mount` or `DIB7_VAULT_KV_MOUNT`. Override a
provider path with `--secret-path` or `DIB7_VAULT_AWS_SECRET_PATH` /
`DIB7_VAULT_GCP_SECRET_PATH` / `DIB7_VAULT_OPENSTACK_SECRET_PATH` /
`DIB7_VAULT_VSPHERE_SECRET_PATH`; keep the
corresponding Terraform runner setting aligned with that path.

The AWS and GCP runners select an entry from `aws_projects` or `gcp_projects`
using its Ansible key or provider project/account ID. The vSphere runner
matches explicit `--target-vcenter` selectors against a `vsphere_projects`
key or hostname. With no explicit selector, flat legacy vCenter credentials
take precedence when present, matching dib7; otherwise a single mapped
entry is selected automatically. For multiple mapped entries, pass
`--target-project` or `--target-vcenter` before the Terraform command, or set
the corresponding AWS, GCP, or vSphere target environment variable. OpenStack
matches a project key, project name, or project ID using `--target-project` or
`DIB7_OPENSTACK_TARGET_PROJECT`; with no explicit selector, legacy
`openstack_auth` credentials take precedence when present, matching dib7.
Otherwise one `openstack_projects` entry is selected automatically.

Create the sync policy with:

```bash
vault policy write dib7-deploy-vault-sync policies/dib7-deploy-vault-sync.hcl
```

The source file remains encrypted in `dib7`. HashiCorp Vault is a runtime
mirror, not an independent place to edit these provider settings. Vault KV
keeps version history for each sync. Each sync replaces the active data at its
provider path with the complete source document and creates a new KV version;
older versions remain available for rollback. Synchronize after each source
change.
