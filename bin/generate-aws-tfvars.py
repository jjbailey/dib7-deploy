#!/usr/bin/env python3
# bin/generate-aws-tfvars.py
# vim: set tabstop=4 shiftwidth=4 expandtab:

from catalog_tfvars import generate

if __name__ == "__main__":
    raise SystemExit(
        generate("aws", "ami", "Generate AWS tfvars from the latest published AMI catalog entry.")
    )
