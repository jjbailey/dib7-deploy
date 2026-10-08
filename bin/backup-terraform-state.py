#!/usr/bin/env python3
# bin/backup-terraform-state.py
# vim: set tabstop=4 shiftwidth=4 expandtab:

"""Copy Terraform state snapshots to a user-selected external destination."""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INVENTORY = REPO_ROOT / "inventory"
PROVIDERS = ("aws", "gcp", "openstack", "vsphere")

class BackupError(Exception):
    """An actionable local state backup error."""

def backup_state(
    destination: Path,
    *,
    inventory: Path = INVENTORY,
    repo_root: Path = REPO_ROOT,
    timestamp: str | None = None,
) -> Path:
    destination = destination.expanduser().resolve()
    repo_root = repo_root.resolve()
    if destination == repo_root or repo_root in destination.parents:
        raise BackupError("backup destination must be outside the repository")

    state_files = []
    for provider in PROVIDERS:
        provider_dir = inventory / provider
        if not provider_dir.exists():
            continue
        state_files.extend(
            path
            for path in provider_dir.rglob("*")
            if not path.is_symlink()
            and path.is_file()
            and (path.name == "terraform.tfstate" or path.name.startswith("terraform.tfstate."))
        )
    state_files.sort()
    if not state_files:
        raise BackupError(f"no Terraform state files found under {inventory}")

    timestamp = timestamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    backup_dir = destination / timestamp
    try:
        backup_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
        for source in state_files:
            relative = source.relative_to(inventory)
            target = backup_dir / relative
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            shutil.copy2(source, target)
            target.chmod(0o600)
    except OSError as exc:
        raise BackupError(f"could not create state backup at {backup_dir}: {exc}") from exc

    return backup_dir

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Back up Terraform state files to an external directory."
    )
    parser.add_argument(
        "destination",
        type=Path,
        help="external backup directory, such as a mounted backup drive",
    )
    args = parser.parse_args(argv)
    try:
        backup_dir = backup_state(args.destination)
    except BackupError as exc:
        print(f"Terraform state backup failed: {exc}", file=sys.stderr)
        return 1
    print(f"Backed up Terraform state to {backup_dir}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
