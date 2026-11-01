#!/usr/bin/env python3
# bin/generate-azure-tfvars.py
# vim: set tabstop=4 shiftwidth=4 expandtab:

from catalog_tfvars import generate

if __name__ == "__main__":
    raise SystemExit(
        generate(
            "azure",
            "managed_image",
            "Generate Azure tfvars from the latest published managed image catalog entry.",
        )
    )
