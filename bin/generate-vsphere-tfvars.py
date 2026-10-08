#!/usr/bin/env python3
# bin/generate-vsphere-tfvars.py
# vim: set tabstop=4 shiftwidth=4 expandtab:

from catalog_tfvars import generate

if __name__ == "__main__":
    raise SystemExit(
        generate(
            "vsphere",
            "content_library_template",
            "Generate vSphere tfvars from the latest published content library template catalog entry.",
        )
    )
