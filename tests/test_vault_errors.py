#!/usr/bin/env python3
# tests/test_vault_errors.py
# vim: set tabstop=4 shiftwidth=4 expandtab:

"""Ensure provider runners preserve useful Vault CLI errors."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

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
        for provider in ("aws", "gcp", "openstack", "vsphere"):
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

if __name__ == "__main__":
    unittest.main()
