#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/services/mcp                                                                #
# Filename   : parse.py                                                                            #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Tuesday April 21st 2026                                                             #
# Modified   : Saturday June 27th 2026 10:40:59 am                                                 #
# ================================================================================================ #
"""Parser for FastMCP ToolResult / CallToolResult objects."""

from __future__ import annotations

import json
from typing import Any

from fastmcp.tools import ToolResult
from mcp.types import CallToolResult

from sciven.domain import Entity, EntityType
from sciven.domain.document import Document
from sciven.domain.reflection import Reflection
from sciven.domain.run import Run
from sciven.domain.signal import Signal
from sciven.domain.source import Source
from sciven.infra.web_search.base import Search


# ================================================================================================ #
#                                     PARSE RESULT                                                 #
# ================================================================================================ #
class MCPResultParser:
    """Dispatches parsing of a FastMCP ToolResult based on its shape.

    A ToolResult carries an optional ``structured_content`` payload and a
    list of ``TextContent`` blocks. The Sciven tools emit two response
    shapes, which ``parse_result`` distinguishes by whether
    ``structured_content`` is populated:

    - Single-object responses (get, add, upsert, remove, load) set
      ``structured_content`` to the object dict and are parsed as a single
      object.
    - Search responses carry one ``TextContent`` block per item and leave
      ``structured_content`` unset. They are parsed as a list, whether they
      hold zero, one, or many items.

    A not-found single response also leaves ``structured_content`` unset
    and carries a single ``"null"`` block, so it parses to the one-item
    list ``[None]``.

    Attributes:
        data: Parsed payload stored after calling ``parse_result``.

    Examples:
        Instantiate and parse a FastMCP ToolResult:

        >>> parser = MCPResultParser()
        >>> result = parser.parse_result(tool_result)
        >>> isinstance(result, (Entity, list))
        True
    """

    def __init__(self) -> None:
        self._data: dict | list[dict] | list[str] | None = None

    @property
    def data(self) -> dict | list[dict] | list[str] | None:
        """Returns the parsed data."""
        return self._data

    def parse_result(
        self, result: ToolResult | CallToolResult | dict | list[dict]
    ) -> MCPResultParser:
        """Stores the payload from a ToolResult, a dict, or a list of dicts.

        Args:
            result: ToolResult/CallToolResult from a FastMCP tool call, an
                already-extracted single payload dict, or a list of payload dicts.

        Returns:
            Self, for fluent chaining into ``to_entity``.

        Raises:
            TypeError: If the result is none of the supported shapes.
        """
        if isinstance(result, (ToolResult, CallToolResult)):
            structured = getattr(result, "structured_content", None)
            if structured is None:
                structured = getattr(result, "structuredContent", None)
            self._data = structured if structured is not None else self._parse_search_result(result)
        elif isinstance(result, dict) or isinstance(result, list):  # noqa: SIM101
            self._data = result
        else:
            raise TypeError(f"Cannot parse result of type {type(result).__name__}.")
        return self

    def to_entity(self) -> Entity | list[Entity]:
        """Returns the parsed data as an Entity or list of Entities.

        Raises:
            ValueError: If no data has been parsed yet.
        """
        if self._data is None:
            raise ValueError("No data parsed yet. Call parse_result first.")

        if isinstance(self._data, dict):
            return ENTITY_TYPE_MAP[EntityType(self._data["entity_type"])].create(self._data)

        return [
            ENTITY_TYPE_MAP[EntityType(item["entity_type"])].create(item) for item in self._data
        ]

    def _parse_search_result(self, result: Any) -> list[Any]:
        """Parses search-style content blocks into a list of items."""
        content = getattr(result, "content", None) or []
        if len(content) == 0:
            return []

        if len(content) == 1:
            parsed = json.loads(content[0].text)
            return parsed if isinstance(parsed, list) else [parsed]

        return [json.loads(block.text) for block in content]


# ------------------------------------------------------------------------------------------------ #
ENTITY_TYPE_MAP: dict[EntityType, type[Entity]] = {
    EntityType.DOCUMENT: Document,
    EntityType.SIGNAL: Signal,
    EntityType.SEARCH: Search,
    EntityType.REFLECTION: Reflection,
    EntityType.RUN: Run,
    EntityType.SOURCE: Source,
}
