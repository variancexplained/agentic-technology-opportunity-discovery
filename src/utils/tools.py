#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Description: Sciven: The Science of Venture Development                                          #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/utils                                                                       #
# Filename   : tools.py                                                                            #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Wednesday May 27th 2026 09:53:09 pm                                                 #
# Modified   : Sunday May 31st 2026 11:20:33 pm                                                    #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
"""Utilities for MCP tools."""

import json

from fastmcp.tools import ToolResult
from mcp.types import TextContent


# ------------------------------------------------------------------------------------------------ #
#                                       HELPERS                                                    #
# ------------------------------------------------------------------------------------------------ #
def tool_result_single(data: dict | None) -> ToolResult:
    """Build a ToolResult for a single-object response.

    Always includes a TextContent block with the JSON-serialized value
    (or 'null' for None). Populates structured_content only when data
    is not None, so clients can distinguish 'found' from 'not found'
    without parsing the content block.

    Args:
        data: The object to return, or None.

    Returns:
        ToolResult with one TextContent block and structured_content
        populated when data is not None.
    """
    content = [TextContent(type="text", text=json.dumps(data, default=str))]
    if data is None:
        return ToolResult(content=content)
    return ToolResult(content=content, structured_content=data)


def tool_result_list(data: list[dict]) -> ToolResult:
    """Build a ToolResult for a list response.

    Each item becomes its own TextContent block (JSON-serialized).
    structured_content is omitted because FastMCP requires an output
    schema to populate it for list-valued returns.

    Args:
        data: List of objects to return.

    Returns:
        ToolResult with one TextContent block per item.
    """
    return ToolResult(
        content=[TextContent(type="text", text=json.dumps(item, default=str)) for item in data],
    )
