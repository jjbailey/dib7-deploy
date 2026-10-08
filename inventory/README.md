# Local inventory

Store generated or machine-specific deployment inventory under this directory,
separate from Terraform source. The repository ignores files here so local
inventory is not included in normal commits.

Terraform state is plaintext, so protect and back it up with the local
deployment inputs it belongs to. Use `bin/backup-terraform-state.py` to copy
state snapshots to a mounted backup disk or secured share outside this
repository. Do not use this directory as the only copy of data that cannot be
regenerated. Put reusable examples and inventory format documentation in
tracked source or documentation directories instead. See
[`doc/state-management.md`](../doc/state-management.md) for workspaces and
backups.
