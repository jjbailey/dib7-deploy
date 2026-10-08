# Vault credentials for AWS Terraform

The AWS Terraform wrapper reads the selected project entry from HashiCorp
Vault KV v2, exchanges its bootstrap key for temporary AWS STS credentials,
and starts Terraform with those credentials in its environment. HashiCorp
Vault mirrors `dib7/vaults/aws.yml`; that Ansible Vault file is the source
of truth. See [`vault-sync.md`](vault-sync.md) for the sync command. Terraform
does not read the base key directly, and no credential is written to a tfvars
file or returned through a Terraform data resource.

## Prerequisites

- A HashiCorp Vault server with TLS configured and trusted by this host.
- `VAULT_ADDR` and a non-root `VAULT_TOKEN` that can read the selected KV v2
  path. The Vault CLI may also obtain a token from its configured token helper.
- The `vault` CLI, Terraform, Python 3, and the dependencies in
  `requirements.txt`.
- An AWS IAM user access key stored in KV v2. Prefer a base IAM user whose only
  relevant permission is `sts:AssumeRole`, with deployment permissions granted
  to the assumed role. If no role ARN is supplied, the wrapper calls
  `sts:GetSessionToken`; those credentials retain the base IAM user's
  permissions.

Create a dedicated Vault policy. KV v2 read permissions are granted on the
`data/` API path:

```bash
vault policy write dib7-deploy-aws-read policies/dib7-deploy-aws-read.hcl
```

The included policy permits reading `dib7-deploy/aws` from the `secret` mount.
It grants no write or delete access. Adjust the policy if you choose another
mount or path, and attach it to the identity used by the Vault CLI.

Run `bin/sync-ansible-vault-to-hashicorp.py aws` after changing
`dib7/vaults/aws.yml`. It mirrors the full `aws_projects` mapping to
`secret/dib7-deploy/aws`. The wrapper reads `aws_access_key_id`,
`aws_secret_access_key`, and optional `aws_session_token` from the selected
entry; it also accepts the former standalone `access_key` / `secret_key` KV
shape during migration. Set `DIB7_VAULT_AWS_SECRET_PATH` and
`DIB7_VAULT_KV_MOUNT` to use another mirror location.

## Run Terraform

Install the Python dependency into the existing `~/.dib7` environment:

```bash
~/.dib7/bin/python -m pip install -r requirements.txt
```

Initialize Terraform without AWS credentials, then use the wrapper for plans
and applies. It prints the resolved AWS account and role identity and credential
expiration to stderr, then invokes Terraform. Set `AWS_TARGET_PROJECT` to the target account ID before using these examples:

```bash
~/.dib7/bin/python bin/terraform-aws.py init
python3 bin/generate-aws-tfvars.py ubuntu26041-base --region us-west-2 --project ${AWS_TARGET_PROJECT}
~/.dib7/bin/python bin/terraform-aws.py plan \
  -var-file=../../inventory/aws/ubuntu26041-base-project-${AWS_TARGET_PROJECT}.tfvars
```

Generated filenames include the catalog project/account and other non-location
scope, but omit the catalog region. The generated variables still record the
image region. Use `--output` if you need to keep separate tfvars files for
regional catalog variants.

If `aws_projects` contains multiple entries, select the same key or account ID
used in Ansible with `--target-project` before the Terraform command, or set
`DIB7_AWS_TARGET_PROJECT`:

```bash
~/.dib7/bin/python bin/terraform-aws.py --target-project ${AWS_TARGET_PROJECT} plan \
  -var-file=../../inventory/aws/ubuntu26041-base-project-${AWS_TARGET_PROJECT}.tfvars
```

The wrapper's Vault settings can be supplied through environment variables or
flags. For example, to use a different KV path and assume a deploy role:

```bash
export DIB7_VAULT_AWS_SECRET_PATH=production/aws-deploy
export DIB7_AWS_ASSUME_ROLE_ARN=arn:aws:iam::${AWS_TARGET_PROJECT}:role/dib7-tf-deploy
~/.dib7/bin/python bin/terraform-aws.py plan \
  -var-file=../../inventory/aws/ubuntu26041-base-project-${AWS_TARGET_PROJECT}.tfvars
```

The wrapper obtains fresh credentials for each plan or apply invocation, so
the same wrapper can apply a saved plan later without preserving credentials in
that plan. It strips Vault and OpenBao tokens from Terraform's environment.
Temporary AWS credentials are passed only through process memory and the
Terraform child environment; the wrapper does not write them to disk or return
them through Terraform. Never enable verbose process-environment dumps or AWS
SDK logging that could expose keys.

Terraform's local state remains plaintext at
`inventory/aws/terraform.tfstate`. The wrapper flow keeps provider credentials
out of that state; it does not encrypt the state file itself. Back up and
protect the ignored `inventory/` directory.

`--role-arn`, `--session-name`, `--duration-seconds`, `--sts-region`,
`--kv-mount`, and `--secret-path` are also available; run the wrapper with
`--help` for the full options. `init`, `fmt`, `validate`, and Terraform `state`
commands do not fetch AWS credentials.
