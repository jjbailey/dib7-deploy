# Local inventory

Store generated catalog tfvars and machine-specific launch settings under this
directory, separate from Terraform source. The private checkout tracks reviewed
tfvars for reproducible deployments and recovery. Check launch settings for
secrets before committing them. The public export excludes this directory.

Terraform state and state backups are local, ignored files. State is plaintext
and can contain sensitive resource attributes; keep it out of Git and back it
up to a mounted backup disk or secured share with `bin/backup-terraform-state.py`.
Do not use this directory as the only copy of data that cannot be regenerated.
Put reusable examples and inventory format documentation in tracked source or
documentation directories instead. See
[`doc/state-management.md`](../doc/state-management.md) for workspaces and
backups.
