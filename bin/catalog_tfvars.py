#!/usr/bin/env python3
# bin/catalog_tfvars.py
# vim: set tabstop=4 shiftwidth=4 expandtab:

"""Shared catalog selection and tfvars generation for provider entry points."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CATALOG = REPO_ROOT.parent / "dib7" / "catalogs" / "image-catalog.json"
LOGICAL_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
EPOCH_VERSION_RE = re.compile(r"^[0-9]+$")

class CatalogError(Exception):
    """An actionable catalog or selector error."""

def _scope_key(image: dict[str, Any]) -> tuple[Any, ...]:
    scope = image.get("scope", {})
    if not isinstance(scope, dict):
        scope = {}
    return (
        image.get("project"),
        image.get("region"),
        tuple(sorted(scope.items())),
    )

def _describe_scope(image: dict[str, Any]) -> str:
    parts = []
    for field in ("project", "region"):
        value = image.get(field)
        if value is not None:
            parts.append(f"{field}={value}")
    scope = image.get("scope", {})
    if isinstance(scope, dict):
        for key, value in sorted(scope.items()):
            parts.append(f"scope.{key}={value}")
    return ", ".join(parts) if parts else "(no recorded scope)"

def _read_catalog(path: Path) -> list[dict[str, Any]]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise CatalogError(f"cannot read catalog {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise CatalogError(f"catalog is not valid JSON: {path}: {exc}") from exc

    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise CatalogError("catalog must be an object with schema_version 1")
    images = document.get("images")
    if not isinstance(images, list) or any(not isinstance(row, dict) for row in images):
        raise CatalogError("catalog images must be an array of objects")
    required_strings = (
        "logical_name",
        "provider",
        "artifact_id",
        "artifact_type",
        "version",
        "architecture",
        "boot_mode",
        "source_build",
        "status",
    )
    allowed_providers = {"aws", "gcp", "openstack", "vsphere"}
    for index, row in enumerate(images):
        for field in required_strings:
            if not isinstance(row.get(field), str) or not row[field]:
                raise CatalogError(f"images[{index}].{field} must be a non-empty string")
        if row["provider"] not in allowed_providers:
            raise CatalogError(f"images[{index}].provider is not a supported provider")
        if row["status"] not in {"published", "retired"}:
            raise CatalogError(f"images[{index}].status must be published or retired")
        for field in ("project", "region"):
            if field in row and not isinstance(row[field], str):
                raise CatalogError(f"images[{index}].{field} must be a string when present")
        if "ssh_username" in row and (
            not isinstance(row["ssh_username"], str) or not row["ssh_username"].strip()
        ):
            raise CatalogError(f"images[{index}].ssh_username must be a non-empty string")
        if "scope" in row and (
            not isinstance(row["scope"], dict)
            or any(not isinstance(key, str) or not isinstance(value, str) for key, value in row["scope"].items())
        ):
            raise CatalogError(f"images[{index}].scope must be an object of string values")
    return images

def _select_image(
    images: list[dict[str, Any]],
    *,
    provider: str,
    artifact_type: str,
    logical_name: str,
    region: str | None,
    project: str | None,
    scope_selectors: dict[str, str],
) -> dict[str, Any]:
    candidates = [
        row
        for row in images
        if row.get("provider") == provider
        and row.get("artifact_type") == artifact_type
        and row.get("logical_name") == logical_name
        and row.get("status") == "published"
    ]

    if region is not None:
        candidates = [row for row in candidates if row.get("region") == region]
    if project is not None:
        candidates = [row for row in candidates if row.get("project") == project]
    if scope_selectors:
        candidates = [
            row
            for row in candidates
            if isinstance(row.get("scope", {}), dict)
            and all(row.get("scope", {}).get(key) == value for key, value in scope_selectors.items())
        ]

    if not candidates:
        raise CatalogError(
            f"no published {provider}/{artifact_type} entry for {logical_name!r} "
            "matches the supplied scope selectors"
        )

    scopes: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in candidates:
        scopes.setdefault(_scope_key(row), row)
    if len(scopes) > 1:
        available = "; ".join(sorted(_describe_scope(row) for row in scopes.values()))
        raise CatalogError(
            f"{logical_name!r} has entries in multiple target scopes; select one with "
            f"--project, --region, and/or --scope KEY=VALUE. Available: {available}"
        )

    if len(candidates) == 1:
        return candidates[0]

    versions = [row.get("version") for row in candidates]
    if any(not isinstance(version, str) or not EPOCH_VERSION_RE.fullmatch(version) for version in versions):
        found = ", ".join(sorted(str(version) for version in versions))
        raise CatalogError(
            f"cannot determine the latest entry for {logical_name!r}: multiple rows have "
            f"non-epoch versions ({found}); publish with a numeric run_id"
        )

    latest_version = max(versions, key=int)
    latest = [row for row in candidates if row.get("version") == latest_version]
    if len(latest) != 1:
        raise CatalogError(
            f"catalog has {len(latest)} entries for {logical_name!r} at latest version "
            f"{latest_version}; remove duplicate rows before generating tfvars"
        )
    return latest[0]

def _hcl_string(value: str) -> str:
    # JSON string escaping is compatible with HCL string literals.
    return json.dumps(value, ensure_ascii=False)

def _hcl_scope(scope: dict[str, str]) -> str:
    if not scope:
        return "{}"
    entries = [f"{_hcl_string(key)} = {_hcl_string(value)}" for key, value in sorted(scope.items())]
    return "{ " + ", ".join(entries) + " }"

def _render_tfvars(image: dict[str, Any]) -> str:
    values: list[tuple[str, str]] = [
        ("image_logical_name", _hcl_string(image["logical_name"])),
        ("image_artifact_id", _hcl_string(image["artifact_id"])),
        ("image_artifact_type", _hcl_string(image["artifact_type"])),
        ("image_version", _hcl_string(image["version"])),
        ("image_architecture", _hcl_string(image["architecture"])),
        ("image_boot_mode", _hcl_string(image["boot_mode"])),
        (
            "image_ssh_username",
            _hcl_string(image["ssh_username"]) if image.get("ssh_username") is not None else "null",
        ),
        ("image_project", _hcl_string(image["project"]) if image.get("project") is not None else "null"),
        ("image_region", _hcl_string(image["region"]) if image.get("region") is not None else "null"),
        ("image_scope", _hcl_scope(image.get("scope", {}))),
    ]
    lines = ["# Generated from the dib7 image catalog. Do not edit by hand."]
    lines.extend(f"{name} = {value}" for name, value in values)
    return "\n".join(lines) + "\n"

def _default_output(provider: str, image: dict[str, Any]) -> Path:
    parts = [image["logical_name"]]
    # Keep target geography out of generated filenames so providers use one
    # convention. Project/account and non-location scope still identify the
    # entry. vSphere filenames include the content-library value only; the
    # content_library key and vCenter scope are omitted.
    for field in ("project",):
        if image.get(field) is not None:
            parts.append(f"{field}-{image[field]}")
    if provider == "vsphere":
        content_library = image.get("scope", {}).get("content_library")
        if content_library is not None:
            parts.append(content_library)
    else:
        for key, value in sorted(image.get("scope", {}).items()):
            if key.casefold() in {"region", "zone"}:
                continue
            parts.append(f"{key}-{value}")
    filename = "-".join(re.sub(r"[^A-Za-z0-9._-]+", "-", part).strip("-") for part in parts)
    return REPO_ROOT / "inventory" / provider / f"{filename}.tfvars"

def _parse_scope_selector(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("scope selectors must use KEY=VALUE")
    key, selector_value = value.split("=", 1)
    if not key or not selector_value:
        raise argparse.ArgumentTypeError("scope selectors must use non-empty KEY=VALUE")
    return key, selector_value

def generate(provider: str, artifact_type: str, description: str, argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("logical_name", help="dib7 logical image name")
    parser.add_argument(
        "--catalog",
        type=Path,
        default=DEFAULT_CATALOG,
        help=f"catalog JSON (default: {DEFAULT_CATALOG})",
    )
    parser.add_argument("--project", help="catalog project selector; for AWS this is the account ID")
    parser.add_argument("--region", help="catalog region selector")
    parser.add_argument(
        "--scope",
        action="append",
        type=_parse_scope_selector,
        default=[],
        metavar="KEY=VALUE",
        help="scope selector; may be repeated",
    )
    parser.add_argument("--output", type=Path, help="output tfvars path (default: scoped path under inventory/<provider>/)")
    args = parser.parse_args(argv)

    if not LOGICAL_NAME_RE.fullmatch(args.logical_name):
        parser.error("logical_name may contain only letters, digits, dot, underscore, and hyphen, and must start with a letter or digit")

    scope_selectors: dict[str, str] = {}
    for key, value in args.scope:
        if key in scope_selectors and scope_selectors[key] != value:
            parser.error(f"conflicting --scope values for {key!r}")
        scope_selectors[key] = value

    try:
        image = _select_image(
            _read_catalog(args.catalog),
            provider=provider,
            artifact_type=artifact_type,
            logical_name=args.logical_name,
            region=args.region,
            project=args.project,
            scope_selectors=scope_selectors,
        )
        output = args.output or _default_output(provider, image)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(_render_tfvars(image), encoding="utf-8")
    except (CatalogError, OSError, KeyError, TypeError) as exc:
        print(f"{provider} tfvars generation failed: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {output} from {provider} catalog version {image['version']} ({_describe_scope(image)})")
    return 0
