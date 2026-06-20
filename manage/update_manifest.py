"""Update the manifest file."""

import json
import os
import re
import sys


def update_manifest() -> None:
    """Update the manifest file."""
    version = "0.0.0"
    for index, value in enumerate(sys.argv):
        if value in ["--version", "-V"]:
            if index + 1 >= len(sys.argv):
                raise SystemExit("Error: --version requires an argument")
            version = sys.argv[index + 1]

    if not re.match(r"^\d+\.\d+\.\d+$", version):
        raise SystemExit(f"Error: invalid version format: {version}")

    manifest_path = os.path.join(os.getcwd(), "custom_components", "hacs", "manifest.json")
    manifest_path = os.path.abspath(manifest_path)

    with open(manifest_path) as manifestfile:
        manifest = json.load(manifestfile)

    manifest["version"] = version

    with open(manifest_path, "w") as manifestfile:
        manifestfile.write(json.dumps(manifest, indent=4, sort_keys=True))


update_manifest()
