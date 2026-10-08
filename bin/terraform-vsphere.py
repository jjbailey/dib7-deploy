#!/usr/bin/env python3
# bin/terraform-vsphere.py
# vim: set tabstop=4 shiftwidth=4 expandtab:

"""Run the vSphere Terraform root with credentials read from Vault KV v2."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from terraform_runner import (
    NO_CREDENTIAL_COMMANDS,
    VaultError,
    add_runner_arguments,
    read_secret as _read_secret,
    run_terraform,
    terraform_args_or_error,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
VSPHERE_ROOT = REPO_ROOT / "environments" / "vsphere"
DEFAULT_SECRET_PATH = "dib7-deploy/vsphere"
def _select_vcenter(
    data: dict[str, Any], requested: str | None
) -> tuple[str | None, dict[str, Any]]:
    requested = requested.strip() if requested and requested.strip() else None
    centers = data.get("vsphere_projects")
    legacy_fields = (
        "vcenter_hostname",
        "vcenter_username",
        "vcenter_password",
    )
    has_legacy = all(field in data for field in legacy_fields)

    # Match dib7's selection rules: absent an explicit selector, flat
    # legacy credentials take precedence even when vsphere_projects exists.
    if requested is None and has_legacy:
        return None, data

    if isinstance(centers, dict):
        if requested is None and len(centers) > 1:
            raise VaultError(
                "multiple vCenters are in Vault; specify --target-vcenter"
            )
        matches = [
            (str(key), entry)
            for key, entry in centers.items()
            if isinstance(entry, dict)
            and (
                requested is None
                or requested in {str(key), str(entry.get("vcenter_hostname", ""))}
            )
        ]
        if len(matches) != 1:
            raise VaultError(
                "the selected vCenter did not match exactly one Vault entry"
            )
        return matches[0]

    # The source Ansible Vault still accepts its original flat mapping.
    if has_legacy:
        hostname = data.get("vcenter_hostname")
        if requested is not None and requested != str(hostname):
            raise VaultError("the selected vCenter did not match the legacy Vault entry")
        return None, data
    raise VaultError(
        "Vault data must contain vsphere_projects or a legacy vCenter mapping"
    )

def _credentials(
    args: argparse.Namespace,
) -> tuple[dict[str, str], str | None, str, str]:
    data = _read_secret(args.kv_mount, args.secret_path)
    key, center = _select_vcenter(data, args.target_vcenter)
    fields = {
        "vcenter_hostname": "VSPHERE_SERVER",
        "vcenter_username": "VSPHERE_USER",
        "vcenter_password": "VSPHERE_PASSWORD",
    }
    for source_field in fields:
        value = center.get(source_field)
        if not isinstance(value, str) or not value.strip():
            raise VaultError(
                f"{args.secret_path}:{source_field} must be a non-empty string"
            )

    validate_certs = center.get("validate_certs", True)
    if not isinstance(validate_certs, bool):
        raise VaultError(f"{args.secret_path}:validate_certs must be a boolean")
    datacenter = center.get("datacenter", "Datacenter")
    if not isinstance(datacenter, str) or not datacenter.strip():
        raise VaultError(f"{args.secret_path}:datacenter must be a non-empty string")

    environment = {
        target_field: str(center[source_field])
        for source_field, target_field in fields.items()
    }
    environment["VSPHERE_ALLOW_UNVERIFIED_SSL"] = str(not validate_certs).lower()
    return environment, key, center["vcenter_hostname"], datacenter

def _terraform_environment(
    credentials: dict[str, str] | None = None,
    vcenter_key: str | None = None,
    datacenter: str | None = None,
) -> dict[str, str]:
    env = os.environ.copy()
    # Provider authentication always comes from the selected Vault entry for
    # plans and applies. Do not let inherited credentials shadow it.
    for name in (
        "VAULT_TOKEN",
        "VAULT_NAMESPACE",
        "BAO_TOKEN",
        "VSPHERE_SERVER",
        "VSPHERE_USER",
        "VSPHERE_PASSWORD",
        "VSPHERE_ALLOW_UNVERIFIED_SSL",
    ):
        env.pop(name, None)
    env.pop("TF_VAR_target_vcenter_key", None)
    env.pop("TF_VAR_datacenter", None)
    if credentials:
        env.update(credentials)
    if vcenter_key is not None:
        env["TF_VAR_target_vcenter_key"] = vcenter_key
    if datacenter is not None:
        env["TF_VAR_datacenter"] = datacenter
    return env

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Terraform for vSphere with credentials read from Vault KV."
    )
    parser.add_argument(
        "--target-vcenter",
        default=os.environ.get("DIB7_VSPHERE_TARGET_VCENTER"),
        help="Ansible Vault vCenter key or hostname (required when Vault has multiple vCenters)",
    )
    add_runner_arguments(parser, "vsphere", DEFAULT_SECRET_PATH)
    args = parser.parse_args(argv)

    terraform_args = terraform_args_or_error(parser, args.terraform_args, "vsphere")

    credentials = None
    vcenter_key = None
    datacenter = None
    command = terraform_args[0]
    if command not in NO_CREDENTIAL_COMMANDS:
        try:
            credentials, vcenter_key, hostname, datacenter = _credentials(args)
        except VaultError as exc:
            print(f"vSphere Vault credential setup failed: {exc}", file=sys.stderr)
            return 1
        selected = f"key={vcenter_key}, " if vcenter_key is not None else ""
        print(f"Vault vSphere vCenter: {selected}server={hostname}", file=sys.stderr)

    return run_terraform(
        args.terraform_bin,
        VSPHERE_ROOT,
        terraform_args,
        _terraform_environment(credentials, vcenter_key, datacenter),
    )

if __name__ == "__main__":
    raise SystemExit(main())
