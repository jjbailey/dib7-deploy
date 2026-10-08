#!/usr/bin/env python3
# tests/test_terraform_runner.py
# vim: set tabstop=4 shiftwidth=4 expandtab:

"""Unit tests for shared provider Terraform runner behavior."""

from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))

from terraform_runner import (
    NO_CREDENTIAL_COMMANDS,
    add_runner_arguments,
    normalize_terraform_args,
    terraform_args_or_error,
)

class TerraformRunnerTests(unittest.TestCase):
    def test_workspace_management_does_not_fetch_provider_credentials(self) -> None:
        self.assertIn("workspace", NO_CREDENTIAL_COMMANDS)

    def test_normalize_removes_only_a_leading_separator(self) -> None:
        self.assertEqual(normalize_terraform_args(["--", "plan", "-no-color"]), ["plan", "-no-color"])
        self.assertEqual(normalize_terraform_args(["plan", "--", "-no-color"]), ["plan", "--", "-no-color"])

    def test_shared_arguments_use_provider_specific_secret_path(self) -> None:
        parser = argparse.ArgumentParser()
        add_runner_arguments(parser, "gcp", "dib7-deploy/gcp")
        args = parser.parse_args(["plan", "-var=zone=us-west1-b"])
        self.assertEqual(args.secret_path, "dib7-deploy/gcp")
        self.assertEqual(
            terraform_args_or_error(parser, args.terraform_args, "gcp"),
            ["plan", "-var=zone=us-west1-b"],
        )

if __name__ == "__main__":
    unittest.main()
