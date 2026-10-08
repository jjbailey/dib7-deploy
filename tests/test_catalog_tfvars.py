#!/usr/bin/env python3
# tests/test_catalog_tfvars.py
# vim: set tabstop=4 shiftwidth=4 expandtab:

"""Unit tests for catalog selection and generated tfvars."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))

import catalog_tfvars

def image(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "logical_name": "ubuntu26041-base",
        "provider": "aws",
        "artifact_id": "ami-1234abcd",
        "artifact_type": "ami",
        "version": "1790514002",
        "architecture": "amd64",
        "boot_mode": "uefi",
        "source_build": "ubuntu26041-base",
        "status": "published",
        "project": "test-account-id",
        "region": "us-west-2",
        "ssh_username": "ubuntu",
        "scope": {},
    }
    row.update(overrides)
    return row

class CatalogSelectionTests(unittest.TestCase):
    def select(self, rows: list[dict[str, object]], **selectors: object) -> dict[str, object]:
        return catalog_tfvars._select_image(
            rows,
            provider=str(selectors.pop("provider", "aws")),
            artifact_type=str(selectors.pop("artifact_type", "ami")),
            logical_name=str(selectors.pop("logical_name", "ubuntu26041-base")),
            region=selectors.pop("region", None),
            project=selectors.pop("project", None),
            scope_selectors=selectors.pop("scope_selectors", {}),
        )

    def test_selects_highest_numeric_version_within_a_scope(self) -> None:
        older = image(version="1790514001")
        newer = image(version="1790514002", artifact_id="ami-newer")
        selected = self.select([older, newer])
        self.assertEqual(selected["artifact_id"], "ami-newer")

    def test_compares_numeric_versions_when_digit_counts_differ(self) -> None:
        older = image(version="999", artifact_id="ami-older")
        newer = image(version="1000", artifact_id="ami-newer")
        self.assertEqual(self.select([older, newer])["artifact_id"], "ami-newer")

    def test_requires_selectors_when_multiple_scopes_match(self) -> None:
        west = image(region="us-west-2")
        east = image(region="us-east-1", artifact_id="ami-east")
        with self.assertRaisesRegex(catalog_tfvars.CatalogError, "multiple target scopes"):
            self.select([west, east])

    def test_ignores_retired_catalog_rows(self) -> None:
        retired = image(status="retired", version="1790514003", artifact_id="ami-retired")
        published = image()
        self.assertEqual(self.select([retired, published])["artifact_id"], "ami-1234abcd")

    def test_scope_selector_matches_catalog_scope(self) -> None:
        selected = image(
            provider="vsphere",
            artifact_type="content_library_template",
            artifact_id="ubuntu26041-base.tmpl",
            scope={"vcenter": "legacy", "content_library": "Content_Library"},
        )
        result = self.select(
            [selected],
            provider="vsphere",
            artifact_type="content_library_template",
            scope_selectors={"vcenter": "legacy"},
        )
        self.assertEqual(result["artifact_id"], "ubuntu26041-base.tmpl")

    def test_rendering_uses_catalog_login_and_escapes_strings(self) -> None:
        row = image(logical_name='ubuntu"test', ssh_username="ubuntu")
        rendered = catalog_tfvars._render_tfvars(row)
        self.assertIn('image_logical_name = "ubuntu\\\"test"', rendered)
        self.assertIn('image_ssh_username = "ubuntu"', rendered)

    def test_default_names_omit_region_and_keep_provider_scope(self) -> None:
        aws_path = catalog_tfvars._default_output("aws", image())
        self.assertEqual(aws_path.name, "ubuntu26041-base-project-test-account-id.tfvars")

        vsphere_path = catalog_tfvars._default_output(
            "vsphere",
            image(
                provider="vsphere",
                artifact_type="content_library_template",
                project=None,
                scope={"vcenter": "legacy", "content_library": "Content_Library"},
            ),
        )
        self.assertEqual(vsphere_path.name, "ubuntu26041-base-Content_Library.tfvars")

    def test_generate_writes_catalog_values(self) -> None:
        row = image()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            catalog_path = temp_path / "catalog.json"
            output_path = temp_path / "image.tfvars"
            catalog_path.write_text(
                json.dumps({"schema_version": 1, "images": [row]}), encoding="utf-8"
            )
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                result = catalog_tfvars.generate(
                    "aws",
                    "ami",
                    "test catalog generation",
                    ["ubuntu26041-base", "--catalog", str(catalog_path), "--output", str(output_path)],
                )
            self.assertEqual(result, 0)
            self.assertIn('image_artifact_id = "ami-1234abcd"', output_path.read_text(encoding="utf-8"))
            self.assertIn("Wrote", stdout.getvalue())

if __name__ == "__main__":
    unittest.main()
