#!/usr/bin/env python3
# tests/test_vault_sync.py
# vim: set tabstop=4 shiftwidth=4 expandtab:

"""Unit tests for source Ansible Vault shape validation."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
BIN_DIR = REPO_ROOT / "bin"
sys.path.insert(0, str(BIN_DIR))
SCRIPT = BIN_DIR / "sync-ansible-vault-to-hashicorp.py"
SPEC = importlib.util.spec_from_file_location("sync_ansible_vault", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load sync helper {SCRIPT}")
sync_helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync_helper)

class AnsibleVaultValidationTests(unittest.TestCase):
    def read_yaml(self, provider: str, contents: str):
        with (
            patch.object(sync_helper, "_ansible_vault_binary", return_value="ansible-vault"),
            patch.object(
                sync_helper.subprocess,
                "run",
                return_value=SimpleNamespace(stdout=contents),
            ),
        ):
            return sync_helper._read_ansible_vault(provider, Path("source.yml"))

    def test_accepts_provider_project_mapping(self) -> None:
        document = self.read_yaml(
            "openstack",
            "openstack_projects:\n  lab:\n    project_name: lab\n    password: sample\n",
        )
        self.assertEqual(document["openstack_projects"]["lab"]["project_name"], "lab")

    def test_accepts_legacy_provider_mapping(self) -> None:
        document = self.read_yaml(
            "vsphere",
            "vcenter_hostname: vc.example.test\nvcenter_username: user\n"
            "vcenter_password: sample\n",
        )
        self.assertEqual(document["vcenter_hostname"], "vc.example.test")

    def test_rejects_empty_plural_mapping(self) -> None:
        with self.assertRaisesRegex(sync_helper.SyncError, "non-empty openstack_projects"):
            self.read_yaml("openstack", "openstack_projects: {}\n")

    def test_rejects_non_mapping_yaml(self) -> None:
        with self.assertRaisesRegex(sync_helper.SyncError, "YAML mapping"):
            self.read_yaml("gcp", "- not-a-mapping\n- still-not-a-mapping\n")

if __name__ == "__main__":
    unittest.main()
