#!/usr/bin/env python3
"""
Migrate plugin credentials from .env to encrypted DB storage.

Run once after upgrading to v0.8.0:
  python3 scripts/migrate-env-credentials.py

Requires NOUSVIZ_ENCRYPTION_KEY to be set in .env.

For each installed plugin with connections in its manifest:
  1. Reads credential fields (type: password) from .env
  2. Encrypts and stores in the credentials table
  3. Removes the lines from .env

Non-secret fields (host, port, database, user) are left in .env.
"""

import os
import sys
import yaml
from pathlib import Path

# Setup path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
load_dotenv(REPO_ROOT / ".env")

from apps.api.src.plugin_credentials import store_plugin_credential

INSTALLED_DIR = REPO_ROOT / "plugins" / "installed"
UTILITIES_DIR = REPO_ROOT / "plugins" / "utilities"
ENV_PATH = REPO_ROOT / ".env"


def main():
    if not os.environ.get("NOUSVIZ_ENCRYPTION_KEY"):
        print("ERROR: NOUSVIZ_ENCRYPTION_KEY not set in .env")
        print("Generate one: python3 -c \"import secrets; print(secrets.token_hex(32))\"")
        sys.exit(1)

    migrated = 0
    removed_keys = []

    for base_dir in [INSTALLED_DIR, UTILITIES_DIR]:
        if not base_dir.exists():
            continue
        for plugin_dir in sorted(base_dir.iterdir()):
            manifest_path = plugin_dir / "plugin.yaml"
            if not manifest_path.exists():
                continue

            with open(manifest_path) as f:
                manifest = yaml.safe_load(f)

            plugin_id = manifest.get("name", plugin_dir.name)
            connections = manifest.get("connections", [])

            for conn_spec in connections:
                prefix = conn_spec.get("env_prefix", "").upper()
                fields = conn_spec.get("fields", [])

                for field in fields:
                    if field.get("type") != "password":
                        continue

                    field_name = field["name"]
                    env_key = f"{prefix}{field_name.upper()}"
                    val = os.environ.get(env_key)

                    if not val:
                        continue

                    print(f"  Migrating {env_key} → encrypted DB (plugin={plugin_id}, field={field_name})")
                    store_plugin_credential(
                        plugin_id, field_name, val,
                        credential_type=conn_spec.get("type", "api_key"),
                        performed_by="migrate-env-credentials",
                    )
                    removed_keys.append(env_key)
                    migrated += 1

    # Remove migrated keys from .env
    if removed_keys and ENV_PATH.exists():
        lines = ENV_PATH.read_text().splitlines()
        new_lines = [line for line in lines if not any(line.startswith(f"{k}=") for k in removed_keys)]
        ENV_PATH.write_text("\n".join(new_lines) + "\n")
        print(f"\n  Removed {len(removed_keys)} credential lines from .env")

    print(f"\n  Done. Migrated {migrated} credential(s) to encrypted storage.")


if __name__ == "__main__":
    main()
