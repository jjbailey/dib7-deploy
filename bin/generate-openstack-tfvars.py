#!/usr/bin/env python3
# bin/generate-openstack-tfvars.py
# vim: set tabstop=4 shiftwidth=4 expandtab:

from catalog_tfvars import generate

if __name__ == "__main__":
    raise SystemExit(
        generate(
            "openstack",
            "glance_image",
            "Generate OpenStack tfvars from the latest published Glance image catalog entry.",
        )
    )
