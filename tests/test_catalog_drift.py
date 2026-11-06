#!/usr/bin/env python3
# tests/test_catalog_drift.py
# vim: set tabstop=4 shiftwidth=4 expandtab:

"""Unit tests for warning when generated tfvars no longer match the catalog."""

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
import terraform_runner

def image(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "logical_name": "ubuntu26041-base",
        "provider": "openstack",
        "artifact_id": "11111111-old",
        "artifact_type": "glance_image",
        "version": "1790514001",
        "architecture": "amd64",
        "boot_mode": "uefi",
        "source_build": "ubuntu26041-base",
        "status": "published",
        "project": "test-project",
        "region": "test-region",
        "ssh_username": "ubuntu",
    }
    row.update(overrides)
    return row

class CatalogDriftTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.tfvars = self.root / "image.tfvars"
        self.tfvars.write_text(catalog_tfvars._render_tfvars(image()), encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def warnings(self, catalog_rows: list[dict[str, object]], args: list[str] | None = None) -> str:
        catalog = self.root / "catalog.json"
        catalog.write_text(json.dumps({"schema_version": 1, "images": catalog_rows}), encoding="utf-8")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            terraform_runner.report_stale_tfvars(
                "openstack",
                self.root,
                args if args is not None else ["plan", "-var-file=image.tfvars"],
                catalog,
            )
        return stderr.getvalue()

    def test_generated_tfvars_round_trip(self) -> None:
        row = image(scope={"vcenter": "lab \"a\"", "content_library": "Lib = 1"})
        self.tfvars.write_text(catalog_tfvars._render_tfvars(row), encoding="utf-8")
        values = catalog_tfvars.read_generated_tfvars(self.tfvars)
        self.assertIsNotNone(values)
        assert values is not None
        self.assertEqual(values["image_scope"], row["scope"])
        self.assertEqual(values["image_version"], "1790514001")
        self.assertIsNone(catalog_tfvars.read_generated_tfvars(self.root / "missing.tfvars"))

    def test_current_tfvars_do_not_warn(self) -> None:
        self.assertEqual(self.warnings([image()]), "")

    def test_superseded_version_warns(self) -> None:
        output = self.warnings([image(version="1790514002", artifact_id="22222222-new")])
        self.assertIn("catalog now has version 1790514002", output)
        self.assertIn("generate-openstack-tfvars.py", output)

    def test_older_rows_kept_beside_the_newest_still_warn(self) -> None:
        output = self.warnings([image(), image(version="1790514002", artifact_id="ami-new")])
        self.assertIn("1790514002", output)

    def test_removed_entry_warns(self) -> None:
        output = self.warnings([image(region="other-region")])
        self.assertIn("no published catalog entry", output)

    def test_hand_written_settings_and_other_commands_are_ignored(self) -> None:
        (self.root / "launch.tfvars").write_text('flavor_name = "m1.small"\n', encoding="utf-8")
        stale = [image(version="1790514002")]
        self.assertEqual(self.warnings(stale, ["plan", "-var-file=launch.tfvars"]), "")
        self.assertEqual(self.warnings(stale, ["destroy", "-var-file=image.tfvars"]), "")

    def test_separate_var_file_argument_is_resolved_from_the_root(self) -> None:
        output = self.warnings([image(version="1790514002")], ["apply", "-var-file", "image.tfvars"])
        self.assertIn("1790514002", output)

if __name__ == "__main__":
    unittest.main()
