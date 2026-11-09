#!/usr/bin/env python3
# tests/test_vault_errors.py
# vim: set tabstop=4 shiftwidth=4 expandtab:

"""Ensure provider runners preserve useful Vault CLI errors."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parents[1]
BIN_DIR = REPO_ROOT / "bin"
sys.path.insert(0, str(BIN_DIR))

import terraform_runner

def load_runner(provider: str):
    path = REPO_ROOT / "bin" / f"terraform-{provider}.py"
    spec = importlib.util.spec_from_file_location(f"terraform_{provider}_runner", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load provider runner {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class VaultErrorDetailTests(unittest.TestCase):
    def test_vault_cli_detail_is_included_for_each_provider(self) -> None:
        for provider in ("aws", "azure", "gcp", "openstack", "vsphere"):
            with self.subTest(provider=provider):
                module = load_runner(provider)
                self.assertIs(module._read_secret, terraform_runner.read_secret)
                failure = subprocess.CalledProcessError(
                    2,
                    ["vault", "kv", "get"],
                    stderr="Error making API request: permission denied\n",
                )
                with patch.object(terraform_runner.subprocess, "run", side_effect=failure):
                    with self.assertRaises(module.VaultError) as caught:
                        module._read_secret("secret", f"dib7-deploy/{provider}")
                self.assertIn("permission denied", str(caught.exception))

class AwsAccountCheckTests(unittest.TestCase):
    def credentials(self, project: dict, target: str | None) -> tuple:
        module = load_runner("aws")
        sts = MagicMock()
        sts.get_session_token.return_value = {"Credentials": {
            "AccessKeyId": "AK", "SecretAccessKey": "SK", "SessionToken": "ST"}}
        sts.get_caller_identity.return_value = {"Account": "111111111111", "Arn": "arn:test"}
        boto3 = types.SimpleNamespace(session=types.SimpleNamespace(
            Session=lambda **_: types.SimpleNamespace(client=lambda _: sts)))
        args = types.SimpleNamespace(
            kv_mount="secret", secret_path="dib7-deploy/aws", target_project=target,
            access_key_field="aws_access_key_id", secret_key_field="aws_secret_access_key",
            session_token_field=None, role_arn=None, session_name="test",
            duration_seconds=3600, sts_region="us-west-2")
        data = {"aws_projects": {"lab": {"aws_access_key_id": "AK", "aws_secret_access_key": "SK", **project}}}
        with patch.dict(sys.modules, {"boto3": boto3}), \
                patch.object(module, "_read_secret", return_value=data):
            return module, module._temporary_credentials(args)

    def test_matching_account_is_accepted(self) -> None:
        _, (_, account, _) = self.credentials({"aws_account_id": "111111111111"}, "lab")
        self.assertEqual(account, "111111111111")

    def test_no_expected_account_fails_closed(self) -> None:
        module = load_runner("aws")
        with self.assertRaises(module.VaultError) as caught:
            self.credentials({}, "lab")
        self.assertIn("cannot verify the target AWS account", str(caught.exception))

    def test_other_account_is_rejected(self) -> None:
        with self.assertRaises(Exception) as caught:
            self.credentials({"aws_account_id": "222222222222"}, "lab")
        self.assertIn("does not match", str(caught.exception))

if __name__ == "__main__":
    unittest.main()
