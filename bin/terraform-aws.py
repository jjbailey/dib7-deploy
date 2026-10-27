#!/usr/bin/env python3
# bin/terraform-aws.py
# vim: set tabstop=4 shiftwidth=4 expandtab:

"""Run AWS Terraform with credentials read from Vault, optionally exchanged through STS."""

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
    # Match dib7: without an explicit selector, accept the legacy flat
    # project even when a projects map is also present.
    if (
        requested is None
        and isinstance(data.get("aws_region"), str)
        and data["aws_region"].strip()
        and "s3_bucket" in data
        and "vmimport_role_name" in data
    ):
        return data

    projects = data.get("aws_projects")
    if isinstance(projects, dict):
        if requested is None and len(projects) > 1:
            raise VaultError("multiple AWS projects are in Vault; specify --target-project")
        matches = []
        for key, entry in projects.items():
            if not isinstance(entry, dict):
                continue
            account_id = entry.get("aws_account_id")
            if not isinstance(account_id, str) or not account_id.strip():
                account_id = entry.get("account_id")
            profile = entry.get("aws_profile")
            if not isinstance(profile, str) or not profile.strip():
                profile = entry.get("profile")
            aliases = {
                str(key),
                str(account_id or ""),
                str(entry.get("project_id", "")),
                str(profile or ""),
            }
            if requested is None or requested in aliases:
                matches.append(entry)
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
        credentials = sts.assume_role(
            RoleArn=args.role_arn,
            RoleSessionName=args.session_name,
            **duration,
        )["Credentials"]
    elif session_token:
        # These are already temporary credentials. GetSessionToken requires
        # long-term IAM-user credentials, so pass them through unchanged.
        credentials = {
            "AccessKeyId": access_key,
            "SecretAccessKey": secret_key,
            "SessionToken": session_token,
        }
    else:
        credentials = sts.get_session_token(**duration)["Credentials"]

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

    expected_account_ids = set()
    requested = args.target_project.strip() if args.target_project else ""
    if re.fullmatch(r"\d{12}", requested):
        expected_account_ids.add(requested)
    configured_account = project.get("aws_account_id")
    if not isinstance(configured_account, str) or not configured_account.strip():
        configured_account = project.get("account_id")
    if configured_account is not None:
        configured_account = str(configured_account).strip()
        if re.fullmatch(r"\d{12}", configured_account):
            expected_account_ids.add(configured_account)
    if args.role_arn:
        role_account = re.match(r"^arn:[^:]+:iam::(\d{12}):role/", args.role_arn)
        if role_account:
            expected_account_ids.add(role_account.group(1))
    if len(expected_account_ids) > 1:
        raise VaultError(
            "AWS target account selectors disagree: "
            + ", ".join(sorted(expected_account_ids))
        )
    if expected_account_ids:
        expected_account = next(iter(expected_account_ids))
        actual_account = str(identity["Account"])
        if actual_account != expected_account:
            raise VaultError(
                f"authenticated AWS account {actual_account} does not match "
                f"the selected target account {expected_account}"
            )

    expiration = credentials.get("Expiration")
    identity_text = str(identity["Arn"])
    if expiration is not None:
        identity_text += f" (expires {expiration.isoformat()})"
    else:
        identity_text += " (using supplied session credentials)"
    return result, str(identity["Account"]), identity_text

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
        description=(
            "Run Terraform with AWS credentials read from Vault KV and optionally "
            "exchanged through STS."
        ),
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
        help=(
            "Ansible Vault project key, AWS account ID, or profile (required when "
            "Vault has multiple projects)"
        ),
    )
    parser.add_argument(
        "--role-arn",
        default=os.environ.get("DIB7_AWS_ASSUME_ROLE_ARN"),
        help=(
            "optional role to assume; without a role, supplied session credentials "
            "are reused or a token is requested"
        ),
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
        except VaultError as exc:
            print(f"AWS Vault credential setup failed: {exc}", file=sys.stderr)
            return 1
        except Exception as exc:
            # ClientError's string form includes the request. A rejected
            # GetSessionToken or AssumeRole can carry the access key, so print
            # only the error code and message.
            response = getattr(exc, "response", None)
            error = response.get("Error", {}) if isinstance(response, dict) else {}
            if error.get("Code"):
                detail = error["Code"]
                if error.get("Message"):
                    detail += f": {error['Message']}"
            else:
                detail = type(exc).__name__
            print(f"AWS Vault credential setup failed: {detail}", file=sys.stderr)
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
