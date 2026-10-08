#!/usr/bin/env python3
# bin/generate-gcp-tfvars.py
# vim: set tabstop=4 shiftwidth=4 expandtab:

from catalog_tfvars import generate

if __name__ == "__main__":
    raise SystemExit(
        generate(
            "gcp",
            "compute_image",
            "Generate GCP tfvars from the latest published Compute Engine image catalog entry.",
        )
    )
