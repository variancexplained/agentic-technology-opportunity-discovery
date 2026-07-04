# CLAUDE.md

## Stack

- **Runtime:** Python 3.12+
- **LLM client:** anthropic
- **Orchestration:** See `src/orchestrator/`
- **Environment:** conda, env name: `<project-name>`
- **Package manager:** conda preferred; pip only for packages unavailable on conda-forge

---

## Critical Rules

### No Secrets
- NEVER commit `.env` or any file with credentials
- NEVER hardcode API keys, tokens, or passwords in source code
- Use `ANTHROPIC_API_KEY` and other vars from `.env`

### Parallelize Independent Operations
- When multiple async calls are independent, ALWAYS use `asyncio.gather()`
- NEVER await independent operations sequentially

```python
# correct
results = await asyncio.gather(agent_a.run(), agent_b.run())

# wrong -- no dependency between calls
result_a = await agent_a.run()
result_b = await agent_b.run()
```

### No Em Dashes
- NEVER use em dashes (--) in any output, files, or comments
- Use commas, colons, or parentheses instead

---

## Multi-Agent Architecture

Agents live in `src/agents/`. Each agent subclasses `BaseAgent` from `src/agents/base.py`.

The orchestrator in `src/orchestrator/coordinator.py` is the only place that calls multiple agents. Individual agents do NOT call each other directly.

Tools shared across agents live in `src/tools/`.

```
src/
  agents/          individual agents, one file each
  orchestrator/    coordinates agent execution
  tools/           shared utilities (llm client, parsing, etc.)
```

---

## Code Conventions

- Snake_case for Python identifiers, kebab-case for filenames
- Type hints everywhere; avoid `Any`
- No function longer than 50 lines; no file longer than 300 lines
- Tests go in `tests/` mirroring the `src/` layout

---

## Plan Mode

Use plan mode for: new agents, orchestration changes, multi-file edits.
Skip for: single-line fixes, obvious bugs.

Every plan step must have a descriptive name, not just a number.
