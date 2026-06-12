#!/usr/bin/env python3
"""Copy canonical auth adapters from libs/shared-auth/ into every service.

The adapters are vendored per service (each copy resolves `app.domain`
imports against its own service). Edit only the canonical files, then run
this script. The repo guard tests/test_shared_auth_sync.py fails CI if a
copy drifts.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANONICAL_DIR = ROOT / "libs" / "shared-auth"

SERVICES = [
    "membership-intake",
    "membership-service",
    "certificate-service",
    "reporting-service",
]

SHARED_FILES = ["zitadel_auth.py", "fake_auth.py"]


def main() -> int:
    changed = 0
    for filename in SHARED_FILES:
        canonical = CANONICAL_DIR / filename
        if not canonical.exists():
            print(f"FEL: kanonisk fil saknas: {canonical}", file=sys.stderr)
            return 1
        for service in SERVICES:
            target = ROOT / "services" / service / "app" / "adapters" / filename
            if target.exists() and target.read_bytes() == canonical.read_bytes():
                continue
            shutil.copyfile(canonical, target)
            print(f"synkade {target.relative_to(ROOT)}")
            changed += 1
    print(f"klart: {changed} fil(er) uppdaterade")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
