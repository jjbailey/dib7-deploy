#!/usr/bin/env python3
# bin/sync-ansible-vault-to-hashicorp.py
# vim: set tabstop=4 shiftwidth=4 expandtab:

"""Mirror a dib7 Ansible Vault file into HashiCorp Vault KV v2."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_REPO = REPO_ROOT.parent / "dib7"
DEFAULT_KV_MOUNT = "secret"

class SyncError(Exception):
    """An actionable synchronization error that does not expose secret data."""

def _ansible_vault_binary() -> str:
    venv_bin = Path(os.environ.get("DIB7_VENV_BIN", str(Path.home() / ".dib7" / "bin")))
    candidate = venv_bin / "ansible-vault"
    if candidate.is_file() and os.access(candidate, os.X_OK):
        return str(candidate)
    found = shutil.which("ansible-vault")
    if found:
        return found
    raise SyncError("ansible-vault was not found in ~/.dib7/bin or on PATH")

def _read_ansible_vault(provider: str, source_file: Path) -> dict[str, Any]:
    command = [_ansible_vault_binary(), "view"]
    password_file = os.environ.get("VAULT_PASSWORD_FILE")
    default_password_file = Path.home() / ".ssh" / "dib-vault-pass"
    if password_file:
        password_path = Path(password_file).expanduser()
        if not password_path.is_file():
            raise SyncError(f"VAULT_PASSWORD_FILE does not name a readable file: {password_path}")
        command.extend(["--vault-password-file", str(password_path)])
    elif default_password_file.is_file():
        command.extend(["--vault-password-file", str(default_password_file)])
    command.append(str(source_file))

    try:
        result = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise SyncError(
            f"ansible-vault could not read {source_file} (exit status {exc.returncode})"
        ) from exc
    except FileNotFoundError as exc:
        raise SyncError("ansible-vault executable was not found") from exc

    try:
        document = yaml.safe_load(result.stdout)
    except yaml.YAMLError as exc:
        raise SyncError(f"decrypted {provider} vault is not valid YAML") from exc
    if not isinstance(document, dict):
        raise SyncError(f"decrypted {provider} vault must contain a YAML mapping")

    plural_key = f"{provider}_projects"
    legacy_key = {
        "aws": "aws_region",
        "gcp": "gcp_project",
        "openstack": "openstack_auth",
        "vsphere": "vcenter_hostname",
    }[provider]
    entries = document.get(plural_key)
    if entries is not None:
        if not isinstance(entries, dict) or not entries:
            raise SyncError(f"{source_file} must contain a non-empty {plural_key} mapping")
        if any(not isinstance(value, dict) for value in entries.values()):
            raise SyncError(f"every entry in {plural_key} must be a mapping")
    elif legacy_key not in document:
        raise SyncError(f"{source_file} contains neither {plural_key} nor the legacy {legacy_key} mapping")
    return document

def _sync(provider: str, args: argparse.Namespace) -> int:
    source_file = Path(args.source_file).expanduser().resolve()
    if not source_file.is_file():
        raise SyncError(f"Ansible Vault source file does not exist: {source_file}")

    document = _read_ansible_vault(provider, source_file)
    mount = args.kv_mount
    path = args.secret_path
    entry_count = len(document.get(f"{provider}_projects", {})) or 1
    entry_kind = "vCenter" if provider == "vsphere" else "project"
    if args.dry_run:
        print(f"Would mirror {provider} Ansible Vault ({entry_count} {entry_kind} entry/entries) to {mount}/{path}")
        return 0

    vault_bin = shutil.which(args.vault_bin)
    if vault_bin is None:
        raise SyncError(f"Vault CLI executable was not found: {args.vault_bin}")

    # The Vault CLI reads structured request data from stdin. The decrypted
    # provider document is never placed in argv, a temporary file, or output.
    request = json.dumps({"data": document}, separators=(",", ":"), ensure_ascii=False)
    try:
        subprocess.run(
            [vault_bin, "write", "-format=json", f"{mount}/data/{path}", "-"],
            input=request,
            check=True,
            capture_output=True,
            text=True,
            env=os.environ.copy(),
        )
    except subprocess.CalledProcessError as exc:
        raise SyncError(
            f"Vault could not write {mount}/{path} (exit status {exc.returncode})"
        ) from exc

    print(f"Mirrored {provider} Ansible Vault ({entry_count} {entry_kind} entry/entries) to {mount}/{path}")
    return 0

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Copy a dib7 encrypted provider vault into HashiCorp Vault KV v2."
    )
    parser.add_argument(
        "provider",
        choices=("aws", "gcp", "openstack", "vsphere"),
        help="provider vault to mirror",
    )
    parser.add_argument(
        "--source-file",
        help="Ansible Vault YAML file (defaults to dib7/vaults/<provider>.yml)",
    )
    parser.add_argument(
        "--kv-mount",
        default=os.environ.get("DIB7_VAULT_KV_MOUNT", DEFAULT_KV_MOUNT),
        help="HashiCorp Vault KV v2 mount (default: secret)",
    )
    parser.add_argument(
        "--secret-path",
        help="Vault path (defaults to dib7-deploy/<provider>)",
    )
    parser.add_argument("--vault-bin", default="vault", help="HashiCorp Vault CLI executable")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="decrypt and validate the source without writing to HashiCorp Vault",
    )
    args = parser.parse_args(argv)
    args.source_file = args.source_file or str(SOURCE_REPO / "vaults" / f"{args.provider}.yml")
    provider_secret_path = os.environ.get(f"DIB7_VAULT_{args.provider.upper()}_SECRET_PATH")
    args.secret_path = args.secret_path or provider_secret_path or f"dib7-deploy/{args.provider}"

    try:
        return _sync(args.provider, args)
    except SyncError as exc:
        print(f"Vault synchronization failed: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
