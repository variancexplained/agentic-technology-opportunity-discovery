# Agentic AI Project Template

A lean starter for agentic AI projects. Unopinionated about source layout. Opinionated about the things that matter: Claude Code compatibility, security hooks, Python tooling, and directories you'll use.

## Structure

```
.claude/          Claude Code conventions. Mirrors the standard layout.
  commands/       Project-scoped slash commands.
  hooks/          Pre and post tool-use hooks.
  skills/         Skill definitions (skill.md files).
  agents/         Agent definitions.
  settings.json   Hook wiring.
data/             Local data files. Gitignored except .gitkeep.
logs/             Runtime logs. Gitignored except .gitkeep.
notebooks/        Exploratory Jupyter notebooks.
.env.example      Environment variable template. Copy to .env and fill in.
.gitignore        Python + project-specific ignores.
CLAUDE.md         Instructions for AI assistants.
CLAUDE.local.md.example  Personal overrides template.
Makefile          install / test / lint / format.
pyproject.toml    Project metadata, ruff, pytest config.
requirements.txt  Core dependencies.
requirements-dev.txt  Dev dependencies.
```

Add your own source layout under whatever directory makes sense for the project. Add a `tests/` directory when you have code to test.

## What this template gives you

Minimal Claude Code integration: two hooks (secret blocking), two commands (help, commit), empty skills and agents directories ready for content. Works without Claude Code if you don't use it.

Python tooling: ruff for lint and format, pytest for tests, Makefile for the common loops.

A starting dependency list weighted toward agentic AI (LangGraph, postgres checkpointing, Anthropic client, Pydantic). Prune what you don't need.

## What this template skips

No src layout. No web framework, no Docker, no deployment scaffolding, no CI. Add any of these when you need them.

No opinions about how agents, skills, tools, or stores should be organized in your source tree. Different projects need different shapes.

## Getting started

1. Use this repo as a GitHub template and clone your new repo.
2. Update `pyproject.toml` with your project name and details.
3. `make install` to create the venv and install deps.
4. Copy `.env.example` to `.env` and fill in values.
5. Build your project structure under the root.

## Conventions

Documented in `CLAUDE.md`. Short version: snake_case Python, kebab-case filenames, type hints everywhere, Google docstrings with constructor args in the class-level Args section, no em dashes, no leading underscores on module-level names.
