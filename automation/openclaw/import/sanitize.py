"""Tiny local sanitizer runner. Mirrors the n8n Function-node logic.

Usage:
    python3 sanitize.py <profile-name> <payload.json>

Exit codes:
    0 — payload passes the profile
    1 — payload rejected (prints the violation)
    2 — usage / file error
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


PROFILES_PATH = Path(__file__).resolve().parent.parent / "sanitizer" / "profiles.json"

PERSONNUMMER_RE = re.compile(r"\d{6,8}[-\s]?\d{4}")


def _load_profile(name: str) -> dict:
    profiles = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))["profiles"]
    if name not in profiles:
        raise SystemExit(f"unknown profile: {name}")
    return profiles[name]


def _walk(value, profile: dict, path: str = "$") -> None:
    allowed = set(profile["allowed_fields"])
    blocked = [re.compile(p) for p in profile["blocked_patterns"]]
    if isinstance(value, dict):
        for key, sub in value.items():
            if isinstance(key, str):
                if any(p.search(key) for p in blocked):
                    raise SystemExit(f"REJECT: blocked pattern in key at {path}.{key}")
                if key not in allowed:
                    raise SystemExit(f"REJECT: key not allowed at {path}.{key}")
            _walk(sub, profile, f"{path}.{key}")
    elif isinstance(value, list):
        for i, item in enumerate(value):
            _walk(item, profile, f"{path}[{i}]")
    elif isinstance(value, str):
        if PERSONNUMMER_RE.search(value):
            raise SystemExit(f"REJECT: personnummer-like pattern at {path}")


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: sanitize.py <profile-name> <payload.json>", file=sys.stderr)
        return 2
    profile = _load_profile(sys.argv[1])
    payload = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    size = len(json.dumps(payload).encode("utf-8"))
    if size > profile["max_payload_size_bytes"]:
        print(f"REJECT: payload size {size} exceeds limit {profile['max_payload_size_bytes']}", file=sys.stderr)
        return 1
    try:
        _walk(payload, profile)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
