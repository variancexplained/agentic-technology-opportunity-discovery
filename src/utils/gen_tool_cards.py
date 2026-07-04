#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Description: Sciven: The Science of Venture Development                                          #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/utils                                                                       #
# Filename   : gen_tool_cards.py                                                                   #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Thursday June 4th 2026 06:09:31 pm                                                  #
# Modified   : Thursday June 4th 2026 06:22:36 pm                                                  #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
r"""Generate Markdown API cards from FastMCP tool servers for use as skill references.

The sibling :mod:`sciven.utils.docs` documents *classes* by introspecting their
signatures and Google-style docstrings. Tool servers are a different shape: a
``FastMCP`` instance holds a set of decorated functions whose documentation lives
in the ``@mcp.tool(description=...)`` decorator and in ``Annotated[..., Field(
description=...)]`` parameter annotations, not in docstrings. FastMCP resolves all
of that into a JSON Schema per tool, and that schema is the source of truth here.

Imports each target by dotted path -- either a ``FastMCP`` server object
(``sciven.tools.arxiv.mcp``) or a module containing exactly one (``sciven.tools.arxiv``)
-- enumerates its tools, and writes one Markdown card per tool.

Usage:
    python -m sciven.utils.gen_tool_cards --out docs/api --tree \\
        sciven.tools.arxiv \\
        sciven.tools.document

Run it in the environment where the tool servers import (e.g. the ``sciven`` conda
env), since import-based introspection loads each server and its dependencies.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import sys
from pathlib import Path
from typing import Any

from fastmcp import FastMCP


# ------------------------------------------------------------------------------------------------ #
def tool_filename(tool_name: str) -> str:
    """Converts a snake_case tool name to a kebab-case filename stem."""
    return tool_name.replace("_", "-").lower()


# ------------------------------------------------------------------------------------------------ #
def schema_type(node: dict[str, Any], defs: dict[str, Any] | None = None) -> str:
    """Renders a JSON Schema node as a readable type string.

    Handles the shapes FastMCP emits for these tools: scalar ``type`` values,
    ``array`` with ``items``, ``object`` (free-form ``dict`` when
    ``additionalProperties`` is truthy), ``enum``, ``anyOf`` unions (with ``null``
    rendered as Optional), and ``$ref`` into ``$defs``.

    Args:
        node: The schema fragment describing one parameter or item.
        defs: The schema's ``$defs`` table, for resolving ``$ref`` references.

    Returns:
        A human-readable type string such as ``list[str]`` or ``dict | None``.
    """
    defs = defs or {}

    ref = node.get("$ref")
    if ref:
        name = ref.rsplit("/", 1)[-1]
        return schema_type(defs.get(name, {}), defs) if name in defs else name

    if "anyOf" in node:
        parts = [schema_type(sub, defs) for sub in node["anyOf"]]
        non_null = [p for p in parts if p != "None"]
        if "None" in parts and len(non_null) == 1:
            return f"{non_null[0]} | None"
        return " | ".join(parts)

    if "enum" in node:
        return " | ".join(repr(v) for v in node["enum"])

    typ = node.get("type")
    if typ == "array":
        items = node.get("items")
        return f"list[{schema_type(items, defs)}]" if items else "list"
    if typ == "object":
        return "dict" if node.get("additionalProperties") else "object"
    if typ == "null":
        return "None"
    if isinstance(typ, list):
        return " | ".join("None" if t == "null" else t for t in typ)
    return typ or "Any"


def render_param(name: str, node: dict[str, Any], required: bool, defs: dict[str, Any]) -> str:
    """Renders one parameter bullet from its schema node."""
    typ = schema_type(node, defs)
    if required:
        qualifier = "required"
    elif "default" in node:
        qualifier = f"default `{node['default']!r}`"
    else:
        qualifier = "optional"
    desc = (node.get("description") or "").strip() or "_undocumented_"
    return f"- `{name}` (`{typ}`, {qualifier}): {desc}"


# ------------------------------------------------------------------------------------------------ #
def build_tool_card(tool: Any, server_name: str, module: str) -> tuple[str, list[str]]:
    """Builds the full Markdown card for a single tool. Returns (markdown, warnings)."""
    warnings: list[str] = []
    params = tool.parameters or {}
    props: dict[str, Any] = params.get("properties", {})
    required = set(params.get("required", []))
    defs = params.get("$defs", {})

    out = [
        f"# `{tool.name}`",
        "",
        f"_Tool on FastMCP server `{server_name}` (`{module}`)._",
        "",
    ]
    if tool.title:
        out += [f"**{tool.title}**", ""]
    if tool.description:
        out += [tool.description.strip(), ""]

    if props:
        # Required parameters first, each group preserving declaration order.
        ordered = [n for n in props if n in required] + [n for n in props if n not in required]
        out += ["## Parameters", ""]
        out += [render_param(n, props[n], n in required, defs) for n in ordered]
        out += [""]
        for name, node in props.items():
            if not (node.get("description") or "").strip():
                warnings.append(f"{tool.name}: parameter '{name}' has no description")

    out += ["## Returns", ""]
    if tool.output_schema:
        out += [f"`{schema_type(tool.output_schema, tool.output_schema.get('$defs', {}))}`", ""]
    else:
        ret = getattr(tool, "return_type", None)
        ret_name = getattr(ret, "__name__", None) or "ToolResult"
        out += [
            f"Returns a `{ret_name}`. The payload shape is described in the tool "
            "description above.",
            "",
        ]

    if tool.tags:
        out += ["## Tags", "", ", ".join(f"`{t}`" for t in sorted(tool.tags)), ""]

    if warnings:
        out += ["<!-- staleness warnings:", *(f"  - {w}" for w in warnings), "-->", ""]

    return "\n".join(out).rstrip() + "\n", warnings


# ------------------------------------------------------------------------------------------------ #
def resolve_server(dotted: str) -> tuple[FastMCP, str]:
    """Resolves a dotted path to a FastMCP server and its defining module path.

    Accepts either a path to a ``FastMCP`` instance (``pkg.tools.arxiv.mcp``) or to
    a module containing exactly one (``pkg.tools.arxiv``).
    """
    try:
        module = importlib.import_module(dotted)
    except ImportError:
        module_path, _, attr = dotted.rpartition(".")
        if not module_path:
            raise
        module = importlib.import_module(module_path)
        obj = getattr(module, attr)
        if not isinstance(obj, FastMCP):
            raise TypeError(
                f"'{dotted}' resolved to {type(obj).__name__}, not a FastMCP server."
            ) from None
        return obj, module_path

    servers = [(name, obj) for name, obj in vars(module).items() if isinstance(obj, FastMCP)]
    if not servers:
        raise ValueError(f"'{dotted}' contains no FastMCP server instance.")
    if len(servers) > 1:
        names = ", ".join(n for n, _ in servers)
        raise ValueError(
            f"'{dotted}' contains multiple FastMCP servers ({names}); "
            "pass the dotted path to a specific one."
        )
    return servers[0][1], dotted


def card_path(module: str, tool_name: str, out_dir: Path, tree: bool) -> Path:
    """Computes the output path for a tool's card.

    With ``tree``, mirrors the server module under ``out_dir`` and drops the
    top-level package, so tool ``search`` in ``sciven.tools.arxiv`` becomes
    ``<out>/tools/arxiv/search.md``. Otherwise the card is written flat.
    """
    filename = f"{tool_filename(tool_name)}.md"
    if not tree:
        return out_dir / filename
    parts = module.split(".")[1:]  # drop the top-level package
    return out_dir.joinpath(*parts, filename)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate Markdown API cards from FastMCP tool servers."
    )
    parser.add_argument(
        "servers", nargs="+", help="Dotted paths to tool modules or FastMCP servers."
    )
    parser.add_argument("--out", required=True, help="Output directory for cards.")
    parser.add_argument(
        "--tree",
        action="store_true",
        help="Mirror each server's module path under --out (drops the top-level package).",
    )
    args = parser.parse_args(argv)

    out_dir = Path(args.out)
    exit_code = 0
    for dotted in args.servers:
        try:
            server, module = resolve_server(dotted)
        except (ImportError, AttributeError, ValueError, TypeError) as exc:
            print(f"ERROR: {dotted}: {exc}", file=sys.stderr)
            exit_code = 1
            continue
        tools = asyncio.run(server.list_tools())
        for tool in tools:
            card, warnings = build_tool_card(tool, server.name, module)
            path = card_path(module, tool.name, out_dir, args.tree)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(card, encoding="utf-8")
            print(f"wrote {path}")
            for warning in warnings:
                print(f"  WARN {warning}", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
