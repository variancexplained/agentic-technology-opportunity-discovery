#!/usr/bin/env python3
"""Block Secrets Hook (PreToolUse).

Prevents Claude from reading or editing sensitive files.
Exit code 2 = block operation and tell Claude why.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SENSITIVE_FILENAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.staging",
    ".env.development",
    "secrets.json",
    "secrets.yaml",
    "id_rsa",
    "id_ed25519",
    ".npmrc",
    ".pypirc",
    "credentials.json",
    "service-account.json",
}

SENSITIVE_PATTERNS = [
    "aws/credentials",
    ".ssh/",
    "private_key",
    "secret_key",
]


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    tool_name = data.get("tool_name", "")
    file_path = data.get("tool_input", {}).get("file_path", "")

    if not file_path:
        return 0

    path = Path(file_path)

    # Allow writing .env files during initial scaffolding.
    # Block reads/edits which could leak existing secrets.
    if tool_name == "Write" and path.name.startswith(".env"):
        return 0

    if path.name in SENSITIVE_FILENAMES:
        print(
            f"BLOCKED: Access to '{file_path}' denied. Sensitive file.",
            file=sys.stderr,
        )
        return 2

    for pattern in SENSITIVE_PATTERNS:
        if pattern in str(path):
            print(
                f"BLOCKED: Access to '{file_path}' denied. "
                f"Path matches sensitive pattern '{pattern}'.",
                file=sys.stderr,
            )
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
