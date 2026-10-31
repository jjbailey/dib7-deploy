#!/usr/bin/env python3
# bin/terraform-azure.py
# vim: set tabstop=4 shiftwidth=4 expandtab:

"""Run the Azure Terraform root with credentials read from Vault KV v2."""

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
    terraform_environment,
    terraform_args_or_error,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
AZURE_ROOT = REPO_ROOT / "environments" / "azure"
DEFAULT_SECRET_PATH = "dib7-deploy/azure"
# Alternate azurerm authentication sources. Removing them keeps Terraform on
# the Vault service principal instead of a certificate, OIDC token, managed
# identity, or whoever last ran `az login`.
AZURE_ALTERNATE_AUTH_ENV = (
    "ARM_CLIENT_CERTIFICATE",
    "ARM_CLIENT_CERTIFICATE_PASSWORD",
    "ARM_CLIENT_CERTIFICATE_PATH",
    "ARM_CLIENT_ID_FILE_PATH",
    "ARM_CLIENT_SECRET_FILE_PATH",
    "ARM_OIDC_REQUEST_TOKEN",
    "ARM_OIDC_REQUEST_URL",
    "ARM_OIDC_TOKEN",
    "ARM_OIDC_TOKEN_FILE_PATH",
    "ARM_USE_AKS_WORKLOAD_IDENTITY",
    "ARM_USE_OIDC",
    "ARM_MSI_ENDPOINT",
    "ARM_AUXILIARY_TENANT_IDS",
)
AZURE_SERVICE_PRINCIPAL_ENV = (
    "ARM_TENANT_ID",
    "ARM_SUBSCRIPTION_ID",
    "ARM_CLIENT_ID",
    "ARM_CLIENT_SECRET",
)

def _select_project(
    data: dict[str, Any], requested: str | None
) -> tuple[str, dict[str, Any]]:
    requested = requested.strip() if requested and requested.strip() else None
    # Match dib7: Azure never had a flat single-target vault, so only the
    # azure_projects mapping is accepted.
    projects = data.get("azure_projects")
    if not isinstance(projects, dict):
        raise VaultError("Vault data must contain an azure_projects mapping")
    if requested is None and len(projects) > 1:
        raise VaultError("multiple Azure projects are in Vault; specify --target-project")
    matches = [
        (str(key), entry)
        for key, entry in projects.items()
        if isinstance(entry, dict)
        and (
            requested is None
            or requested in {str(key), str(entry.get("subscription_id", ""))}
        )
    ]
    if len(matches) != 1:
        raise VaultError("the selected Azure project did not match exactly one Vault entry")
    return matches[0]

def _credentials(args: argparse.Namespace) -> tuple[dict[str, str], str | None]:
    data = _read_secret(args.kv_mount, args.secret_path)
    key, project = _select_project(data, args.target_project)

    environment = {}
    for field, name in zip(
        ("tenant_id", "subscription_id", "client_id", "client_secret"),
        AZURE_SERVICE_PRINCIPAL_ENV,
    ):
        value = project.get(field)
        if not isinstance(value, str) or not value.strip():
            raise VaultError(
                f"{args.secret_path}:azure_projects[{key!r}].{field} must be a non-empty string"
            )
        environment[name] = value.strip()

    resource_group = project.get("resource_group")
    if resource_group is not None and (
        not isinstance(resource_group, str) or not resource_group.strip()
    ):
        raise VaultError(
            f"{args.secret_path}:azure_projects[{key!r}].resource_group must be a non-empty string"
        )
    return environment, resource_group.strip() if resource_group else None

def _terraform_environment(
    credentials: dict[str, str] | None = None,
    resource_group: str | None = None,
) -> dict[str, str]:
    env = terraform_environment(AZURE_ALTERNATE_AUTH_ENV)
    for name in AZURE_SERVICE_PRINCIPAL_ENV:
        env.pop(name, None)
    # Never fall back to an Azure CLI session or a managed identity.
    env["ARM_USE_CLI"] = "false"
    env["ARM_USE_MSI"] = "false"
    if credentials is not None:
        env.update(credentials)
    if resource_group is not None:
        # Terraform variable files and explicit -var arguments can override
        # this default when deploying to a different resource group.
        env["TF_VAR_resource_group_name"] = resource_group
    return env

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Terraform for Azure with a service principal read from Vault KV."
    )
    parser.add_argument(
        "--target-project",
        default=os.environ.get("DIB7_AZURE_TARGET_PROJECT"),
        help="Ansible Vault project key or Azure subscription ID (required when the Vault has multiple projects)",
    )
    add_runner_arguments(parser, "azure", DEFAULT_SECRET_PATH)
    args = parser.parse_args(argv)

    terraform_args = terraform_args_or_error(parser, args.terraform_args, "azure")

    credentials = None
    resource_group = None
    command = terraform_args[0]
    if command not in NO_CREDENTIAL_COMMANDS:
        try:
            credentials, resource_group = _credentials(args)
        except VaultError as exc:
            print(f"Azure Vault credential setup failed: {exc}", file=sys.stderr)
            return 1
        print(
            f"Vault Azure service principal: {credentials['ARM_CLIENT_ID']}, "
            f"subscription={credentials['ARM_SUBSCRIPTION_ID']}",
            file=sys.stderr,
        )

    return run_terraform(
        args.terraform_bin,
        AZURE_ROOT,
        terraform_args,
        _terraform_environment(credentials, resource_group),
    )

if __name__ == "__main__":
    raise SystemExit(main())
