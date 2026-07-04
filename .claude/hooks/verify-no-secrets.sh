#!/usr/bin/env bash
# Verify No Secrets Hook (Stop).
# Scans staged files for common secret patterns before Claude ends its turn.
# Lightweight: catches the obvious stuff, not a full secret scanner.

set -u

STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null || true)

if [ -z "$STAGED_FILES" ]; then
    exit 0
fi

PATTERNS=(
    'AKIA[0-9A-Z]{16}'
    'sk-[a-zA-Z0-9]{32,}'
    'ANTHROPIC_API_KEY=sk-ant-[a-zA-Z0-9_-]+'
    '-----BEGIN (RSA|OPENSSH|DSA|EC) PRIVATE KEY-----'
    'ghp_[a-zA-Z0-9]{36}'
    'xox[pboar]-[a-zA-Z0-9-]+'
)

FOUND=0
for file in $STAGED_FILES; do
    if [ ! -f "$file" ]; then
        continue
    fi
    for pattern in "${PATTERNS[@]}"; do
        if grep -E "$pattern" "$file" > /dev/null 2>&1; then
            echo "WARNING: Possible secret in $file (pattern: $pattern)" >&2
            FOUND=1
        fi
    done
done

if [ "$FOUND" -eq 1 ]; then
    echo "Refusing to let Claude stop cleanly. Review flagged files before committing." >&2
    exit 1
fi

exit 0
