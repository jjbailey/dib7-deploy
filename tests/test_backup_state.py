#!/usr/bin/env python3
# tests/test_backup_state.py
# vim: set tabstop=4 shiftwidth=4 expandtab:

"""Unit tests for external Terraform state backups."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "bin" / "backup-terraform-state.py"
SPEC = importlib.util.spec_from_file_location("backup_terraform_state", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load state backup helper {SCRIPT}")
backup_helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backup_helper)

class BackupTerraformStateTests(unittest.TestCase):
    def test_copies_default_and_workspace_states_with_restricted_modes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            repo = base / "repo"
            inventory = repo / "inventory"
            default_state = inventory / "aws" / "terraform.tfstate"
            workspace_state = (
                inventory / "aws" / "terraform.tfstate.d" / "test" / "terraform.tfstate"
            )
            default_state.parent.mkdir(parents=True)
            workspace_state.parent.mkdir(parents=True)
            default_state.write_text("default-state", encoding="utf-8")
            workspace_state.write_text("workspace-state", encoding="utf-8")
            destination = base / "external-backups"

            result = backup_helper.backup_state(
                destination,
                inventory=inventory,
                repo_root=repo,
                timestamp="20261006T120000.000000Z",
            )

            self.assertEqual(
                (result / "aws" / "terraform.tfstate").read_text(encoding="utf-8"),
                "default-state",
            )
            self.assertEqual(
                (
                    result
                    / "aws"
                    / "terraform.tfstate.d"
                    / "test"
                    / "terraform.tfstate"
                ).read_text(encoding="utf-8"),
                "workspace-state",
            )
            self.assertEqual((result.stat().st_mode & 0o777), 0o700)
            self.assertEqual(((result / "aws" / "terraform.tfstate").stat().st_mode & 0o777), 0o600)

    def test_rejects_backups_inside_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            inventory = repo / "inventory"
            (inventory / "aws").mkdir(parents=True)
            (inventory / "aws" / "terraform.tfstate").write_text("state", encoding="utf-8")
            with self.assertRaisesRegex(backup_helper.BackupError, "outside the repository"):
                backup_helper.backup_state(
                    repo / "backup", inventory=inventory, repo_root=repo
                )

if __name__ == "__main__":
    unittest.main()
