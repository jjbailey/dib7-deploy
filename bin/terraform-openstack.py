#!/usr/bin/env python3
# bin/terraform-openstack.py
# vim: set tabstop=4 shiftwidth=4 expandtab:

"""Run the OpenStack Terraform root with credentials read from Vault KV v2."""

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
OPENSTACK_ROOT = REPO_ROOT / "environments" / "openstack"
DEFAULT_SECRET_PATH = "dib7-deploy/openstack"
OPENSTACK_AUTH_ENV = (
    "OS_AUTH_URL",
    "OS_USERNAME",
    "OS_PASSWORD",
    "OS_PROJECT_NAME",
    "OS_PROJECT_ID",
    "OS_TENANT_NAME",
    "OS_TENANT_ID",
    "OS_USER_DOMAIN_NAME",
    "OS_USER_DOMAIN_ID",
    "OS_PROJECT_DOMAIN_NAME",
    "OS_PROJECT_DOMAIN_ID",
    "OS_REGION_NAME",
    "OS_AUTH_TYPE",
    "OS_TOKEN",
    "OS_AUTH_TOKEN",
    "OS_CLOUD",
    "OS_CLIENT_CONFIG_FILE",
    "OS_IDENTITY_API_VERSION",
    "OS_INSECURE",
    "OS_CACERT",
    "OS_ENDPOINT_TYPE",
)

def _select_project(
    data: dict[str, Any], requested: str | None
) -> tuple[str | None, dict[str, Any]]:
    requested = requested.strip() if requested and requested.strip() else None
    projects = data.get("openstack_projects")
    legacy = data.get("openstack_auth")

    # Keep dib7's selection behavior: with no explicit project, legacy
    # credentials take precedence over a project map when both are present.
    if (
        requested is None
        and isinstance(legacy, dict)
        and str(legacy.get("project_name", "")).strip()
    ):
        return None, legacy

    if isinstance(projects, dict):
        if requested is None and len(projects) > 1:
            raise VaultError(
                "multiple OpenStack projects are in Vault; specify --target-project"
            )
        matches = [
            (str(key), entry)
            for key, entry in projects.items()
            if isinstance(entry, dict)
            and (
                requested is None
                or requested
                in {
                    str(key),
                    str(entry.get("project_name", "")),
                    str(entry.get("project_id", "")),
                }
            )
        ]
        if len(matches) != 1:
            raise VaultError(
                "the selected OpenStack project did not match exactly one Vault entry"
            )
        key, entry = matches[0]
        project_name = entry.get("project_name")
        if project_name is not None and str(project_name) != key:
            raise VaultError(
                f"openstack_projects[{key!r}].project_name does not match its Vault key"
            )
        return key, entry

    raise VaultError(
        "Vault data must contain openstack_projects or a legacy openstack_auth mapping"
    )

def _credentials(
    args: argparse.Namespace,
) -> tuple[dict[str, str], str | None, str, str | None, str | None]:
    data = _read_secret(args.kv_mount, args.secret_path)
    key, project = _select_project(data, args.target_project)

    required_fields = ("auth_url", "username", "password")
    for field in required_fields:
        value = project.get(field)
        if not isinstance(value, str) or not value.strip():
            raise VaultError(
                f"{args.secret_path}:{field} must be a non-empty string"
            )

    project_name_value = project.get("project_name")
    if (
        isinstance(project_name_value, bool)
        or not isinstance(project_name_value, (str, int))
        or not str(project_name_value).strip()
    ):
        raise VaultError(
            f"{args.secret_path}:project_name must be a non-empty string or integer"
        )
    project_name = str(project_name_value)

    environment = {
        "OS_AUTH_URL": project["auth_url"],
        "OS_USERNAME": project["username"],
        "OS_PASSWORD": project["password"],
        "OS_PROJECT_NAME": project_name,
    }
    optional_fields = {
        "user_domain_name": "OS_USER_DOMAIN_NAME",
        "user_domain_id": "OS_USER_DOMAIN_ID",
        "project_domain_name": "OS_PROJECT_DOMAIN_NAME",
        "project_domain_id": "OS_PROJECT_DOMAIN_ID",
        "region_name": "OS_REGION_NAME",
    }
    for source_field, target_field in optional_fields.items():
        value = project.get(source_field)
        if value is not None:
            if not isinstance(value, str) or not value.strip():
                raise VaultError(
                    f"{args.secret_path}:{source_field} must be a non-empty string"
                )
            environment[target_field] = value

    project_id_value = project.get("project_id")
    if project_id_value is not None and (
        isinstance(project_id_value, bool)
        or not isinstance(project_id_value, (str, int))
        or not str(project_id_value).strip()
    ):
        raise VaultError(
            f"{args.secret_path}:project_id must be a non-empty string or integer"
        )
    project_id = str(project_id_value) if project_id_value is not None else None
    if project_id is not None:
        # OpenStack SDK gives project-name precedence when both are set.
        # Prefer the explicit ID when the Vault entry provides one.
        environment.pop("OS_PROJECT_NAME", None)
        environment["OS_PROJECT_ID"] = project_id

    region = project.get("region_name")
    return environment, key, project_name, project_id, region

def _terraform_environment(
    credentials: dict[str, str] | None = None,
    region: str | None = None,
) -> dict[str, str]:
    env = terraform_environment(
        (
        *OPENSTACK_AUTH_ENV,
        "TF_VAR_target_region",
        )
    )
    if credentials:
        env.update(credentials)
    if region is not None:
        env["TF_VAR_target_region"] = region
    return env

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Terraform for OpenStack with credentials read from Vault KV."
    )
    parser.add_argument(
        "--target-project",
        default=os.environ.get("DIB7_OPENSTACK_TARGET_PROJECT"),
        help="Ansible Vault project key, project name, or project ID",
    )
    add_runner_arguments(parser, "openstack", DEFAULT_SECRET_PATH)
    args = parser.parse_args(argv)

    terraform_args = terraform_args_or_error(parser, args.terraform_args, "openstack")

    credentials = None
    project_name = None
    project_id = None
    region = None
    key = None
    command = terraform_args[0]
    if command not in NO_CREDENTIAL_COMMANDS:
        try:
            credentials, key, project_name, project_id, region = _credentials(args)
        except VaultError as exc:
            print(f"OpenStack Vault credential setup failed: {exc}", file=sys.stderr)
            return 1
        selected = f"key={key}, " if key is not None else ""
        project_id_label = (
            f" (id={project_id})"
            if project_id is not None and project_id != project_name
            else ""
        )
        selected_region = f", region={region}" if region else ""
        print(
            f"Vault OpenStack project: {selected}{project_name}{project_id_label}{selected_region}",
            file=sys.stderr,
        )

    return run_terraform(
        args.terraform_bin,
        OPENSTACK_ROOT,
        terraform_args,
        _terraform_environment(credentials, region),
    )

if __name__ == "__main__":
    raise SystemExit(main())
