# Terraform state and deployments

Each provider has a local state file under `inventory/<provider>/`. State and
state backups are ignored by Git because they can contain sensitive values;
keep them local and back them up securely. The public export also excludes
`inventory/`. The `default` workspace continues to use the existing
`terraform.tfstate` path.
Additional CLI workspaces have separate state files under
`inventory/<provider>/terraform.tfstate.d/<workspace>/terraform.tfstate`.

After updating this repository, initialize each root with its wrapper. If
Terraform reports a backend configuration change, back up the current state,
then reinitialize that root with `init -reconfigure`. This updates Terraform's
backend configuration without migrating state. The existing default state path
has not moved. For example:

```bash
python3 bin/terraform-vsphere.py init -reconfigure
```

Run the equivalent command for each provider root that reports the change. To
keep multiple deployments of the same provider root, create and select a
separate workspace for each deployment **before** planning or applying. Set
`AWS_TARGET_PROJECT` to the target account ID and, if it differs,
`AWS_CATALOG_PROJECT` to the AMI owner account ID first. These shell variables
select the tfvars file; the wrapper reads Vault's target from
`DIB7_AWS_TARGET_PROJECT` or `--target-project`:

```bash
: "${AWS_TARGET_PROJECT:?Set the target AWS account ID}"
python3 bin/terraform-aws.py init
python3 bin/terraform-aws.py workspace new "aws-${AWS_TARGET_PROJECT}-us-west-2-ubuntu26041-base"
python3 bin/terraform-aws.py plan \
  -var-file="../../inventory/aws/ubuntu26041-base-project-${AWS_CATALOG_PROJECT:-$AWS_TARGET_PROJECT}.tfvars"
```

Use `workspace select NAME` to return to an existing deployment. Terraform
workspaces isolate state, but they do not isolate credentials or access. Use
them for deployments managed by the same operator and credential scope; they
are not a security boundary for separate accounts or teams. Review the selected
workspace with `workspace show` before applying. A workspace name does not
change the cloud resource name: set distinct `instance_name` or `vm_name`
values in launch settings when the provider requires names to be unique.

The local smoke scripts choose a workspace from provider, target and image by
default. Set `DEPLOYMENT_WORKSPACE` to select another name. Their new default
workspaces do not adopt resources already in the `default` workspace.

The local backend locks state during Terraform operations, but the state still
resides on this machine. It can include cloud IDs, addresses, metadata, SSH
public keys, and provider-sensitive attributes. Do not commit it. Back it up to
a mounted backup disk or secured backup share:

```bash
python3 bin/backup-terraform-state.py /mnt/secure-backups/dib7-deploy
```

Each run creates a timestamped directory and copies the default and named
workspace state files with owner-only file permissions. Keep the backup
destination outside this repository and protect it like a secret.
This command backs up state only; it does not back up generated tfvars or
launch settings.

The wrappers do not fetch Vault credentials for `fmt`, `init`, `output`,
`providers`, `show`, `state`, `validate`, `version`, or `workspace` commands.
`state` subcommands can change the state, and `output` can display values
stored in it, so use those commands carefully even though they do not contact a
cloud provider.
