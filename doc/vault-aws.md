# Vault credentials for AWS Terraform

The AWS Terraform wrapper reads the selected project entry from HashiCorp
Vault KV v2 and starts Terraform with AWS credentials in its environment. With
a role ARN, it calls `AssumeRole`. Without one, it reuses a supplied session
token or calls `GetSessionToken` using long-term IAM-user credentials.
HashiCorp Vault mirrors `dib7/vaults/aws.yml`; that Ansible Vault file is
the source of truth. See [`vault-sync.md`](vault-sync.md) for the sync command.
Terraform does not read the base key directly, and no credential is written to
a tfvars file or returned through a Terraform data resource.

## Prerequisites

- A HashiCorp Vault server with TLS configured and trusted by this host.
- `VAULT_ADDR` and a non-root `VAULT_TOKEN` that can read the selected KV v2
  path. The Vault CLI may also obtain a token from its configured token helper.
- The `vault` CLI, Terraform, Python 3, and the dependencies in
  `requirements.txt`.
- An AWS IAM user access key stored in KV v2. Prefer a base IAM user whose only
  relevant permission is `sts:AssumeRole`, with deployment permissions granted
  to the assumed role. With no role ARN and no stored session token, the
  wrapper calls `sts:GetSessionToken`; those credentials retain the base IAM
  user's permissions. If the entry has an `aws_session_token`, that session is
  used as-is when no role ARN is supplied, or as the base credentials for
  `AssumeRole` when a role is supplied.

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
and applies. It prints the resolved AWS account and caller identity to stderr, along with
credential expiration when STS returns it, then invokes Terraform. Set
`AWS_TARGET_PROJECT` to the deployment account ID and pass it to the wrapper as
`DIB7_AWS_TARGET_PROJECT`; this selects the matching Vault entry when there
are multiple entries. Use `AWS_CATALOG_PROJECT` when the AMI is owned by a
different account; otherwise they can be the same:

```bash
: "${AWS_TARGET_PROJECT:?Set the target AWS account ID}"
export DIB7_AWS_TARGET_PROJECT="$AWS_TARGET_PROJECT"
~/.dib7/bin/python bin/terraform-aws.py init
python3 bin/generate-aws-tfvars.py ubuntu26041-base --region us-west-2 --project "${AWS_CATALOG_PROJECT:-$AWS_TARGET_PROJECT}"
~/.dib7/bin/python bin/terraform-aws.py plan \
  -var-file="../../inventory/aws/ubuntu26041-base-project-${AWS_CATALOG_PROJECT:-$AWS_TARGET_PROJECT}-region-us-west-2.tfvars"
```

Generated filenames include the catalog project/account and region, so
different regional images have separate tfvars files.

If `aws_projects` contains multiple entries, select the same key, account ID, or
profile used in Ansible with `--target-project` before the Terraform command,
or set `DIB7_AWS_TARGET_PROJECT`. When the selected entry, target selector, or
role ARN provides an account ID, the wrapper checks the authenticated AWS
account against it and stops before Terraform if they disagree:

```bash
~/.dib7/bin/python bin/terraform-aws.py --target-project ${AWS_TARGET_PROJECT} plan \
  -var-file=../../inventory/aws/ubuntu26041-base-project-${AWS_CATALOG_PROJECT:-$AWS_TARGET_PROJECT}-region-us-west-2.tfvars
```

The wrapper's Vault settings can be supplied through environment variables or
flags. For example, to use a different KV path and assume a deploy role:

```bash
export DIB7_VAULT_AWS_SECRET_PATH=production/aws-deploy
export DIB7_AWS_ASSUME_ROLE_ARN=arn:aws:iam::${AWS_TARGET_PROJECT}:role/dib7-tf-deploy
~/.dib7/bin/python bin/terraform-aws.py plan \
  -var-file=../../inventory/aws/ubuntu26041-base-project-${AWS_CATALOG_PROJECT:-$AWS_TARGET_PROJECT}-region-us-west-2.tfvars
```

The wrapper resolves credentials for each plan or apply invocation, so the
same wrapper can apply a saved plan later without preserving credentials in
that plan. When it uses long-term IAM-user credentials, it requests a new STS
session; supplied session credentials are passed through as-is, and assumed-role
credentials are obtained through `AssumeRole`. It strips Vault and OpenBao
tokens from Terraform's environment.

Temporary AWS credentials are passed only through process memory and the
Terraform child environment; the wrapper does not write them to disk or return
them through Terraform. Never enable verbose process-environment dumps or AWS
SDK logging that could expose keys.

Terraform's local state remains plaintext at
`inventory/aws/terraform.tfstate` (or `inventory/aws/terraform.tfstate.d/<workspace>/`
for a named workspace). The wrapper flow keeps provider credentials
out of that state; it does not encrypt the state file itself. State is ignored
by Git. Protect it and back it up outside the repository.

These options are also available, each with an environment variable:

| Option                  | Environment variable                 | Default                                        |
| ----------------------- | ------------------------------------ | ---------------------------------------------- |
| `--role-arn`            | `DIB7_AWS_ASSUME_ROLE_ARN`           | none (reuses token or calls `GetSessionToken`) |
| `--session-name`        | `DIB7_AWS_SESSION_NAME`              | `dib7-deploy`                              |
| `--duration-seconds`    | `DIB7_AWS_SESSION_DURATION_SECONDS`  | 3600                                           |
| `--sts-region`          | `DIB7_AWS_STS_REGION`                | `us-west-2`                                    |
| `--access-key-field`    | `DIB7_VAULT_AWS_ACCESS_KEY_FIELD`    | `aws_access_key_id`                            |
| `--secret-key-field`    | `DIB7_VAULT_AWS_SECRET_KEY_FIELD`    | `aws_secret_access_key`                        |
| `--session-token-field` | `DIB7_VAULT_AWS_SESSION_TOKEN_FIELD` | none                                           |
| `--kv-mount`            | `DIB7_VAULT_KV_MOUNT`                | `secret`                                       |
| `--secret-path`         | `DIB7_VAULT_AWS_SECRET_PATH`         | `dib7-deploy/aws`                          |

The duration must be at least 900 seconds, and at most 43200 when assuming a
role or 129600 for a requested session token. The session name, used with a
role, must be 2–64 characters from letters, digits, and `_+=,.@-`. When a session token is
supplied without assuming a role, that token is used as-is and the duration
setting does not renew or extend it. Run the wrapper with
`--help` for the full options. `init`, `fmt`, `validate`, and Terraform `state`
commands do not fetch AWS credentials.
