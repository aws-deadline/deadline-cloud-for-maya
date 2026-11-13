# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Point an installed Maya at a network license server.

GUI Maya asks which license type to use on first launch unless the Autodesk
Licensing service already has a license method for it, and nothing can answer
that prompt in CI. This registers Maya with the NETWORK method and the given
server using AdskLicensingInstHelper, which ships with the Autodesk Licensing
service that the Maya installer adds.

The product key and version are read from the helper's own list of installed
products, so a new Maya release needs no change here.

Usage: python configure-maya-license.py --version 2027 --server 27002@127.0.0.1
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional


def find_helper() -> Path:
    """Locate AdskLicensingInstHelper for this platform."""
    system = platform.system()
    if system == "Windows":
        common = os.environ.get("CommonProgramFiles(x86)", r"C:\Program Files (x86)\Common Files")
        helper = (
            Path(common)
            / "Autodesk Shared"
            / "AdskLicensing"
            / "Current"
            / "helper"
            / "AdskLicensingInstHelper.exe"
        )
    elif system == "Darwin":
        helper = Path(
            "/Library/Application Support/Autodesk/AdskLicensing/Current/helper/AdskLicensingInstHelper"
        )
    else:
        helper = Path("/opt/Autodesk/AdskLicensing/Current/helper/AdskLicensingInstHelper")
    if not helper.is_file():
        raise FileNotFoundError(
            f"AdskLicensingInstHelper not found at {helper}; is Maya installed?"
        )
    return helper


def find_maya_product(
    products: list[dict[str, Any]], maya_version: str
) -> Optional[dict[str, Any]]:
    """Return the helper's entry for the given Maya year, e.g. "2027"."""
    for product in products:
        if product.get("feature_id") != "MAYA":
            continue
        version = str(product.get("sel_prod_ver") or product.get("def_prod_ver") or "")
        if version.startswith(f"{maya_version}."):
            return product
    return None


def change_command(helper: Path, product: dict[str, Any], server: str) -> list[str]:
    return [
        str(helper),
        "change",
        "--pk",
        str(product.get("sel_prod_key") or product["def_prod_key"]),
        "--pv",
        str(product.get("sel_prod_ver") or product["def_prod_ver"]),
        "--lm",
        "NETWORK",
        "--lt",
        "SINGLE",
        "--ls",
        server,
    ]


def list_products(helper: Path) -> list[dict[str, Any]]:
    result = subprocess.run([str(helper), "list"], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--version", required=True, help="Maya year, for example 2027")
    parser.add_argument("--server", required=True, help="License server as port@host")
    args = parser.parse_args()

    helper = find_helper()
    product = find_maya_product(list_products(helper), args.version)
    if product is None:
        print(f"ERROR: Maya {args.version} is not registered with Autodesk Licensing")
        return 1
    subprocess.run(change_command(helper, product, args.server), check=True)

    configured = find_maya_product(list_products(helper), args.version) or {}
    servers = configured.get("lic_servers") or []
    if args.server not in servers:
        print(f"ERROR: license servers are {servers}, expected {args.server}")
        return 1
    print(f"Maya {args.version} uses network license server {args.server}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
