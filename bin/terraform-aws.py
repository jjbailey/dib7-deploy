#!/usr/bin/env python3
# bin/terraform-aws.py
# vim: set tabstop=4 shiftwidth=4 expandtab:

"""Run the AWS Terraform root using short-lived credentials fetched via Vault."""

from __future__ import annotations

import argparse
import os
import re
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
AWS_ROOT = REPO_ROOT / "environments" / "aws"
DEFAULT_SECRET_PATH = "dib7-deploy/aws"
SESSION_NAME_RE = re.compile(r"^[A-Za-z0-9_+=,.@-]{2,64}$")

def _required_secret_any(data: dict[str, Any], fields: list[str], path: str) -> str:
    fields = list(dict.fromkeys(fields))
    for field in fields:
        value = data.get(field)
        if isinstance(value, str) and value.strip():
            return value
    names = " or ".join(repr(field) for field in fields)
    raise VaultError(f"{path} is missing a non-empty {names} value")

def _select_project(data: dict[str, Any], requested: str | None) -> dict[str, Any]:
    requested = requested.strip() if requested and requested.strip() else None
    projects = data.get("aws_projects")
    if isinstance(projects, dict):
        if requested is None and len(projects) > 1:
            raise VaultError("multiple AWS projects are in Vault; specify --target-project")
        matches = [
            entry
            for key, entry in projects.items()
            if isinstance(entry, dict)
            and (
                requested is None
                or requested
                in {
                    str(key),
                    str(entry.get("aws_account_id", "")),
                    str(entry.get("project_id", "")),
                }
            )
        ]
        if len(matches) != 1:
            raise VaultError("the selected AWS project did not match exactly one Vault entry")
        return matches[0]

    # Accept the former standalone HashiCorp KV fields during migration and
    # the legacy flat Ansible Vault mapping.
    if any(field in data for field in ("aws_access_key_id", "access_key", "aws_region")):
        return data
    raise VaultError("Vault data must contain aws_projects or a legacy AWS project mapping")

def _temporary_credentials(args: argparse.Namespace) -> tuple[dict[str, str], str, str]:
    try:
        import boto3
    except ImportError as exc:
        raise VaultError("boto3 is required; install the project dependencies from requirements.txt") from exc

    data = _read_secret(args.kv_mount, args.secret_path)
    project = _select_project(data, args.target_project)
    access_key = _required_secret_any(
        project,
        [args.access_key_field, "aws_access_key_id", "access_key"],
        args.secret_path,
    )
    secret_key = _required_secret_any(
        project,
        [args.secret_key_field, "aws_secret_access_key", "secret_key"],
        args.secret_path,
    )
    session_fields = ([args.session_token_field] if args.session_token_field else []) + [
        "aws_session_token",
        "session_token",
    ]
    session_token = next(
        (
            project[field]
            for field in session_fields
            if isinstance(project.get(field), str) and project[field].strip()
        ),
        None,
    )

    base_session = boto3.session.Session(
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        aws_session_token=session_token or None,
        region_name=args.sts_region,
    )
    sts = base_session.client("sts")
    duration = {"DurationSeconds": args.duration_seconds}
    if args.role_arn:
        response = sts.assume_role(
            RoleArn=args.role_arn,
            RoleSessionName=args.session_name,
            **duration,
        )
    else:
        response = sts.get_session_token(**duration)

    credentials = response["Credentials"]
    result = {
        "AWS_ACCESS_KEY_ID": str(credentials["AccessKeyId"]),
        "AWS_SECRET_ACCESS_KEY": str(credentials["SecretAccessKey"]),
        "AWS_SESSION_TOKEN": str(credentials["SessionToken"]),
    }
    identity = boto3.session.Session(
        aws_access_key_id=result["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=result["AWS_SECRET_ACCESS_KEY"],
        aws_session_token=result["AWS_SESSION_TOKEN"],
        region_name=args.sts_region,
    ).client("sts").get_caller_identity()
    expiration = credentials["Expiration"].isoformat()
    return result, str(identity["Account"]), f"{identity['Arn']} (expires {expiration})"

def _terraform_environment(credentials: dict[str, str] | None = None) -> dict[str, str]:
    # Prevent inherited provider selectors from shadowing Vault credentials.
    env = terraform_environment(
        (
            "AWS_PROFILE",
            "AWS_DEFAULT_PROFILE",
            "AWS_WEB_IDENTITY_TOKEN_FILE",
            "AWS_ROLE_ARN",
        )
    )
    if credentials:
        env.update(credentials)
    return env

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Terraform for AWS with temporary credentials obtained through Vault KV."
    )
    parser.add_argument(
        "--access-key-field",
        default=os.environ.get("DIB7_VAULT_AWS_ACCESS_KEY_FIELD", "aws_access_key_id"),
        help="selected project field containing the base AWS access key ID",
    )
    parser.add_argument(
        "--secret-key-field",
        default=os.environ.get("DIB7_VAULT_AWS_SECRET_KEY_FIELD", "aws_secret_access_key"),
        help="selected project field containing the base AWS secret access key",
    )
    parser.add_argument(
        "--session-token-field",
        default=os.environ.get("DIB7_VAULT_AWS_SESSION_TOKEN_FIELD"),
        help="optional KV field containing a base AWS session token",
    )
    parser.add_argument(
        "--target-project",
        default=os.environ.get("DIB7_AWS_TARGET_PROJECT"),
        help="Ansible Vault project key or AWS account ID (required when Vault has multiple projects)",
    )
    parser.add_argument(
        "--role-arn",
        default=os.environ.get("DIB7_AWS_ASSUME_ROLE_ARN"),
        help="optional role to assume; defaults to a session token for the base IAM user",
    )
    parser.add_argument(
        "--session-name",
        default=os.environ.get("DIB7_AWS_SESSION_NAME", "dib7-deploy"),
        help="CloudTrail session name when assuming a role",
    )
    parser.add_argument(
        "--duration-seconds",
        type=int,
        default=int(os.environ.get("DIB7_AWS_SESSION_DURATION_SECONDS", "3600")),
        help="STS credential lifetime in seconds (default: 3600)",
    )
    parser.add_argument(
        "--sts-region",
        default=os.environ.get("DIB7_AWS_STS_REGION", "us-west-2"),
        help="AWS region used for STS API calls (default: us-west-2)",
    )
    add_runner_arguments(parser, "aws", DEFAULT_SECRET_PATH)
    args = parser.parse_args(argv)

    terraform_args = terraform_args_or_error(parser, args.terraform_args, "aws")

    command = terraform_args[0]
    credentials: dict[str, str] | None = None
    if command not in NO_CREDENTIAL_COMMANDS:
        if not 900 <= args.duration_seconds <= (43200 if args.role_arn else 129600):
            parser.error("duration must be 900 seconds or more and within the AWS STS maximum for this credential type")
        if args.role_arn and not SESSION_NAME_RE.fullmatch(args.session_name):
            parser.error("session name must be 2–64 characters using letters, digits, or _+=,.@-")
        try:
            credentials, account, identity = _temporary_credentials(args)
        except Exception as exc:
            print(f"AWS Vault credential setup failed: {exc}", file=sys.stderr)
            return 1
        print(f"Vault AWS identity: account={account}, {identity}", file=sys.stderr)

    return run_terraform(
        args.terraform_bin,
        AWS_ROOT,
        terraform_args,
        _terraform_environment(credentials),
    )

if __name__ == "__main__":
    raise SystemExit(main())
