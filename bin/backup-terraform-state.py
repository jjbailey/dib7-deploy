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
PROVIDERS = ("aws", "azure", "gcp", "openstack", "vsphere")

class BackupError(Exception):
    """An actionable local state backup error."""

def backup_state(
    destination: Path,
    *,
    inventory: Path = INVENTORY,
    repo_root: Path = REPO_ROOT,
    timestamp: str | None = None,
    force: bool = False,
) -> Path:
    destination = destination.expanduser().resolve()
    repo_root = repo_root.resolve()
    if destination == repo_root or repo_root in destination.parents:
        raise BackupError("backup destination must be outside the repository")

    state_files = []
    locked = []
    for provider in PROVIDERS:
        provider_dir = inventory / provider
        if not provider_dir.exists():
            continue
        # The local backend writes .terraform.tfstate.lock.info beside a state
        # file while an operation holds it; a copy taken then may be torn.
        for path in provider_dir.rglob("*"):
            if path.name == ".terraform.tfstate.lock.info":
                locked.append(path)
            elif (
                not path.is_symlink()
                and path.is_file()
                and (path.name == "terraform.tfstate" or path.name.startswith("terraform.tfstate."))
            ):
                state_files.append(path)
    if locked and not force:
        held = ", ".join(str(path.parent.relative_to(inventory)) for path in sorted(locked))
        raise BackupError(
            f"Terraform state is locked in {held}; wait for the running operation "
            "to finish or rerun with --force"
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
    parser.add_argument(
        "--force",
        action="store_true",
        help="copy state even while a Terraform operation holds its lock",
    )
    args = parser.parse_args(argv)
    try:
        backup_dir = backup_state(args.destination, force=args.force)
    except BackupError as exc:
        print(f"Terraform state backup failed: {exc}", file=sys.stderr)
        return 1
    print(f"Backed up Terraform state to {backup_dir}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
