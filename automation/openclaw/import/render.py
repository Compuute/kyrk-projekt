"""Tiny helper: substitute {{data}} in a prompt template with a local JSON file.

Usage:
    python3 render.py <template.json> <data.json>

Prints the rendered system + user prompts so you can eyeball them without
calling the API.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: render.py <template.json> <data.json>", file=sys.stderr)
        return 2
    template = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    data = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    user_prompt = template["user_prompt_template"].replace(
        "{{data}}", json.dumps(data, ensure_ascii=False, indent=2)
    )
    print("=== SYSTEM ===")
    print(template["system_prompt"])
    print()
    print("=== USER ===")
    print(user_prompt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
