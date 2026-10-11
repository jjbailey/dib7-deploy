#!/usr/bin/env python3
# tests/test_provider_selection.py
# vim: set tabstop=4 shiftwidth=4 expandtab:

"""Unit tests for provider-specific Vault project and vCenter selection."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BIN_DIR = REPO_ROOT / "bin"
sys.path.insert(0, str(BIN_DIR))

def load_runner(provider: str):
    path = BIN_DIR / f"terraform-{provider}.py"
    spec = importlib.util.spec_from_file_location(f"terraform_{provider}_runner", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load provider runner {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class ProviderSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.aws = load_runner("aws")
        cls.gcp = load_runner("gcp")
        cls.openstack = load_runner("openstack")
        cls.vsphere = load_runner("vsphere")

    def test_aws_project_selection_by_account_id(self) -> None:
        selected = self.aws._select_project(
            {"aws_projects": {"production": {"aws_account_id": "test-account-id"}}},
            "test-account-id",
        )
        self.assertEqual(selected["aws_account_id"], "test-account-id")

    def test_aws_requires_a_selector_for_multiple_projects(self) -> None:
        with self.assertRaisesRegex(self.aws.VaultError, "multiple AWS projects"):
            self.aws._select_project({"aws_projects": {"one": {}, "two": {}}}, None)

    def test_gcp_project_selection_by_project_id(self) -> None:
        selected = self.gcp._select_project(
            {"gcp_projects": {"lab": {"gcp_project": "lab-project-id"}}},
            "lab-project-id",
        )
        self.assertEqual(selected["gcp_project"], "lab-project-id")

    def test_gcp_accepts_legacy_flat_mapping(self) -> None:
        selected = self.gcp._select_project(
            {"gcp_project": "lab-project-id", "service_account_key": {"type": "service_account"}},
            None,
        )
        self.assertEqual(selected["gcp_project"], "lab-project-id")

    def test_openstack_legacy_credentials_take_precedence_without_selector(self) -> None:
        legacy = {"project_name": "legacy-project"}
        data = {
            "openstack_auth": legacy,
            "openstack_projects": {"mapped": {"project_name": "mapped"}},
        }
        key, selected = self.openstack._select_project(data, None)
        self.assertIsNone(key)
        self.assertIs(selected, legacy)

    def test_openstack_project_selection_by_project_id(self) -> None:
        key, selected = self.openstack._select_project(
            {
                "openstack_projects": {
                    "lab": {"project_name": "lab", "project_id": "123"}
                }
            },
            "123",
        )
        self.assertEqual(key, "lab")
        self.assertEqual(selected["project_id"], "123")

    def test_vcenter_legacy_credentials_take_precedence_without_selector(self) -> None:
        legacy = {
            "vcenter_hostname": "vc.example.test",
            "vcenter_username": "user",
            "vcenter_password": "placeholder",
        }
        data = {
            **legacy,
            "vsphere_projects": {"mapped": {"vcenter_hostname": "other.example.test"}},
        }
        key, selected = self.vsphere._select_vcenter(data, None)
        self.assertEqual(key, "legacy")
        self.assertIs(selected, data)

    def test_vcenter_mapping_can_be_selected_by_hostname(self) -> None:
        key, selected = self.vsphere._select_vcenter(
            {"vsphere_projects": {"legacy": {"vcenter_hostname": "vc.example.test"}}},
            "vc.example.test",
        )
        self.assertEqual(key, "legacy")
        self.assertEqual(selected["vcenter_hostname"], "vc.example.test")

if __name__ == "__main__":
    unittest.main()
