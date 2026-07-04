---
description: List available commands in this project
scope: project
allowed-tools: Read, Glob
---

# Help

List all available Claude Code commands in this project.

## Step 1 — Enumerate

Glob `.claude/commands/*.md` to find all command files. For each file, read the YAML frontmatter to extract `description`.

## Step 2 — Display

Format a short reference list:

```
=== Commands ===

/help      List available commands
/commit    Review and commit staged changes
```

Keep it short. No flourish.
