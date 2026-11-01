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
from unittest.mock import patch

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
        cls.azure = load_runner("azure")
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

    def test_azure_project_selection_by_subscription_id(self) -> None:
        key, selected = self.azure._select_project(
            {
                "azure_projects": {
                    "lab": {"subscription_id": "test-subscription-id"},
                    "other": {"subscription_id": "other-subscription-id"},
                }
            },
            "test-subscription-id",
        )
        self.assertEqual(key, "lab")
        self.assertEqual(selected["subscription_id"], "test-subscription-id")

    def test_azure_requires_a_selector_for_multiple_projects(self) -> None:
        with self.assertRaisesRegex(self.azure.VaultError, "multiple Azure projects"):
            self.azure._select_project({"azure_projects": {"one": {}, "two": {}}}, None)

    def test_azure_has_no_legacy_flat_mapping(self) -> None:
        with self.assertRaisesRegex(self.azure.VaultError, "azure_projects"):
            self.azure._select_project({"subscription_id": "test-subscription-id"}, None)

    def test_azure_environment_uses_only_the_vault_service_principal(self) -> None:
        credentials = {
            "ARM_TENANT_ID": "test-tenant",
            "ARM_SUBSCRIPTION_ID": "test-subscription",
            "ARM_CLIENT_ID": "test-client",
            "ARM_CLIENT_SECRET": "placeholder",
        }
        with patch.dict(
            self.azure.os.environ,
            {"ARM_USE_OIDC": "true", "ARM_CLIENT_CERTIFICATE_PATH": "/tmp/cert.pfx", "VAULT_TOKEN": "x"},
        ):
            env = self.azure._terraform_environment(credentials, "rg-test")
        self.assertEqual(env["ARM_CLIENT_ID"], "test-client")
        self.assertEqual(env["ARM_USE_CLI"], "false")
        self.assertEqual(env["TF_VAR_resource_group_name"], "rg-test")
        for name in ("ARM_USE_OIDC", "ARM_CLIENT_CERTIFICATE_PATH", "VAULT_TOKEN"):
            self.assertNotIn(name, env)

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
