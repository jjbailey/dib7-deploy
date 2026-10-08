#!/usr/bin/env python3
# bin/terraform_runner.py
# vim: set tabstop=4 shiftwidth=4 expandtab:

"""Shared Vault and Terraform command handling for provider runners."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

NO_CREDENTIAL_COMMANDS = frozenset(
    {
        "fmt",
        "init",
        "output",
        "providers",
        "show",
        "state",
        "validate",
        "version",
        "workspace",
    }
)

COMMON_CREDENTIAL_ENV = ("VAULT_TOKEN", "VAULT_NAMESPACE", "BAO_TOKEN")

def terraform_environment(extra_names: tuple[str, ...] = ()) -> dict[str, str]:
    """Copy the process environment without inherited credential selectors."""
    environment = os.environ.copy()
    for name in (*COMMON_CREDENTIAL_ENV, *extra_names):
        environment.pop(name, None)
    return environment

class VaultError(Exception):
    """An actionable Vault credential or KV response error."""

def add_runner_arguments(
    parser: argparse.ArgumentParser,
    provider: str,
    default_secret_path: str,
) -> None:
    """Add command-line arguments shared by all provider runners."""
    parser.add_argument(
        "--kv-mount",
        default=os.environ.get("DIB7_VAULT_KV_MOUNT", "secret"),
        help="Vault KV v2 mount (default: secret)",
    )
    parser.add_argument(
        "--secret-path",
        default=os.environ.get(
            f"DIB7_VAULT_{provider.upper()}_SECRET_PATH", default_secret_path
        ),
        help=(
            "path within the KV mount "
            f"(default can be set with DIB7_VAULT_{provider.upper()}_SECRET_PATH)"
        ),
    )
    parser.add_argument("--terraform-bin", default="terraform", help="Terraform executable")
    parser.add_argument(
        "terraform_args", nargs=argparse.REMAINDER, help="Terraform command and arguments"
    )

def terraform_args_or_error(
    parser: argparse.ArgumentParser,
    args: list[str],
    provider: str,
) -> list[str]:
    """Normalize trailing Terraform arguments and require a command."""
    terraform_args = normalize_terraform_args(args)
    if not terraform_args:
        parser.error(
            "provide a Terraform command, for example: "
            f"plan -var-file=../../inventory/{provider}/image.tfvars"
        )
    return terraform_args

def read_secret(mount: str, path: str) -> dict[str, Any]:
    """Read an object from a Vault KV v2 mount without printing its contents."""
    try:
        result = subprocess.run(
            ["vault", "kv", "get", "-format=json", f"-mount={mount}", path],
            check=True,
            capture_output=True,
            text=True,
            env=os.environ.copy(),
        )
    except FileNotFoundError as exc:
        raise VaultError("vault CLI was not found on PATH") from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip() or f"exit status {exc.returncode}"
        raise VaultError(f"Vault could not read {mount}/{path}: {detail}") from exc

    try:
        payload = json.loads(result.stdout)
        data = payload["data"]["data"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise VaultError("Vault returned an unexpected KV v2 JSON response") from exc
    if not isinstance(data, dict):
        raise VaultError("Vault KV data is not an object")
    return data

def normalize_terraform_args(args: list[str]) -> list[str]:
    """Remove the optional separator accepted by the provider wrappers."""
    return args[1:] if args and args[0] == "--" else args

def run_terraform(
    terraform_bin: str,
    root: Path,
    terraform_args: list[str],
    environment: dict[str, str],
) -> int:
    """Run Terraform from a provider root and report a missing executable."""
    try:
        return subprocess.run(
            [terraform_bin, f"-chdir={root}", *terraform_args],
            env=environment,
        ).returncode
    except FileNotFoundError:
        print(f"Terraform executable not found: {terraform_bin}", file=sys.stderr)
        return 127
