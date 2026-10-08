#!/usr/bin/env python3
# bin/terraform-gcp.py
# vim: set tabstop=4 shiftwidth=4 expandtab:

"""Run the GCP Terraform root with credentials fetched from Vault KV v2."""

from __future__ import annotations

import argparse
import json
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
GCP_ROOT = REPO_ROOT / "environments" / "gcp"
DEFAULT_SECRET_PATH = "dib7-deploy/gcp"
def _select_project(data: dict[str, Any], requested: str | None) -> dict[str, Any]:
    requested = requested.strip() if requested and requested.strip() else None
    projects = data.get("gcp_projects")
    if isinstance(projects, dict):
        matches = [
            entry
            for key, entry in projects.items()
            if isinstance(entry, dict)
            and (
                requested is None
                or requested
                in {
                    str(key),
                    str(entry.get("gcp_project", "")),
                    str(entry.get("project_id", "")),
                }
            )
        ]
        if requested is None and len(projects) > 1:
            raise VaultError("multiple GCP projects are in Vault; specify --target-project")
        if len(matches) != 1:
            raise VaultError("the selected GCP project did not match exactly one Vault entry")
        return matches[0]

    # Continue to accept the old standalone KV object and the legacy flat
    # Ansible Vault shape while the canonical source is mirrored.
    if "service_account_key" in data or "gcp_project" in data:
        return data
    raise VaultError("Vault data must contain gcp_projects or a legacy GCP project mapping")

def _credentials(args: argparse.Namespace) -> tuple[str, str, str | None]:
    data = _read_secret(args.kv_mount, args.secret_path)
    project = _select_project(data, args.target_project)
    value = project.get("service_account_key")
    if isinstance(value, str):
        try:
            info = json.loads(value)
        except json.JSONDecodeError as exc:
            raise VaultError(
                f"{args.secret_path}:service_account_key is not valid service-account JSON"
            ) from exc
    else:
        info = value
    if not isinstance(info, dict) or info.get("type") != "service_account":
        raise VaultError(
            f"{args.secret_path}:service_account_key must contain a GCP service-account key object"
        )
    for field in ("client_email", "private_key", "token_uri"):
        if not isinstance(info.get(field), str) or not info[field].strip():
            raise VaultError(
                f"{args.secret_path}:service_account_key is missing {field!r}"
            )
    project_id = project.get("gcp_project", project.get("project_id"))
    if project_id is not None and (not isinstance(project_id, str) or not project_id.strip()):
        raise VaultError(f"{args.secret_path}:gcp_project must be a non-empty string")
    return json.dumps(info, separators=(",", ":")), info["client_email"], project_id

def _terraform_environment(
    credentials_json: str | None = None,
    project_id: str | None = None,
) -> dict[str, str]:
    # Keep alternate Google credential sources out of Terraform's environment.
    env = terraform_environment(
        (
            "GOOGLE_APPLICATION_CREDENTIALS",
            "GOOGLE_CLOUD_KEYFILE_JSON",
            "GCLOUD_KEYFILE_JSON",
            "GOOGLE_OAUTH_ACCESS_TOKEN",
            "CLOUDSDK_AUTH_ACCESS_TOKEN",
        )
    )
    if credentials_json is not None:
        env["GOOGLE_CREDENTIALS"] = credentials_json
    else:
        env.pop("GOOGLE_CREDENTIALS", None)
    if project_id is not None:
        # Terraform variable files and explicit -var arguments can override
        # this default when deploying to a different project.
        env["TF_VAR_project_id"] = project_id
    return env

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Terraform for GCP with a service-account key read from Vault KV."
    )
    parser.add_argument(
        "--target-project",
        default=os.environ.get("DIB7_GCP_TARGET_PROJECT"),
        help="Ansible Vault project key or GCP project ID (required when the Vault has multiple projects)",
    )
    add_runner_arguments(parser, "gcp", DEFAULT_SECRET_PATH)
    args = parser.parse_args(argv)

    terraform_args = terraform_args_or_error(parser, args.terraform_args, "gcp")

    credentials_json = None
    project_id = None
    command = terraform_args[0]
    if command not in NO_CREDENTIAL_COMMANDS:
        try:
            credentials_json, service_account_email, project_id = _credentials(args)
        except VaultError as exc:
            print(f"GCP Vault credential setup failed: {exc}", file=sys.stderr)
            return 1
        identity = f"Vault GCP service account: {service_account_email}"
        if project_id:
            identity += f", project={project_id}"
        print(identity, file=sys.stderr)

    return run_terraform(
        args.terraform_bin,
        GCP_ROOT,
        terraform_args,
        _terraform_environment(credentials_json, project_id),
    )

if __name__ == "__main__":
    raise SystemExit(main())
