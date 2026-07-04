#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/services/source                                                             #
# Filename   : source.py                                                                           #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Monday April 20th 2026                                                              #
# Modified   : Monday June 29th 2026 06:49:32 am                                                   #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
"""MCP server for the Source stage of the Sciven pipeline."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.tools import ToolResult
from pydantic import Field

from sciven.harness.tools import DATABASE_URI, EMBEDDING_CONFIG, set_embedding_config
from sciven.infra.persistence.provider.langgraph.store import StoreAdapter
from sciven.infra.persistence.repo.source import SourceRepo
from sciven.utils.tools import tool_result_list, tool_result_single

logger = logging.getLogger(__name__)

# ruff: noqa: D103

# ------------------------------------------------------------------------------------------------ #
#                                     CONFIGURATION                                                #
# ------------------------------------------------------------------------------------------------ #
mcp = FastMCP("sciven-source")
set_embedding_config()  # Ensure embedding config is initialized before any repos or tools are used


# ================================================================================================ #
#                                     SOURCE TOOLS                                                 #
# ================================================================================================ #
@mcp.tool(
    name="get",
    description=(
        "Retrieves a single source profile by namespace and key.\n\n"
        "Expects 'namespace' as a 2-part list of [stage, entity_type] "
        "(e.g. ['discovery', 'source']), and 'key' as the source 'id'.\n\n"
        "Produces the full serialized source dict on success (name, "
        "description, url, source_type, entity_name, tier), or null if "
        "no source exists with that key.\n\n"
        "Use this tool to look up a specific source by its id, for "
        "example to check if it exists before adding, or to read its "
        "current source_type, entity_name, and tier."
    ),
)
def get(
    namespace: Annotated[
        list[str],
        Field(
            description="Source namespace as [stage, entity_type], e.g. ['discovery', 'source'].",
        ),
    ],
    key: Annotated[
        str,
        Field(
            description="The source 'id' used as the store key.",
        ),
    ],
) -> ToolResult:
    try:
        with StoreAdapter(DATABASE_URI, EMBEDDING_CONFIG) as adapter:
            repo = SourceRepo(adapter)
            source = repo.get(tuple(namespace), key)
            if source is None:
                return tool_result_single(None)
            return tool_result_single(source.as_dict())
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc


@mcp.tool(
    name="search",
    description=(
        "Searches source profiles within a namespace using optional semantic "
        "text and metadata filters.\n\n"
        "Expects 'namespace' as a 2-part list of [stage, entity_type] defining "
        "the search scope (e.g. ['discovery', 'source'] to search all "
        "discover-stage sources). Optional 'query' performs semantic "
        "similarity against source name and description. Optional 'filter' "
        "matches exact values on stored fields, e.g. "
        "{'source_type': 'paper'}, {'entity_name': 'innovation'}, or "
        "{'tier': 1}. 'limit' caps results (default 10).\n\n"
        "Produces a list of serialized source dicts ranked by relevance.\n\n"
        "Use this tool to find sources matching a research topic, or to "
        "retrieve all sources of a given source_type, entity_name, or tier."
    ),
)
def search(
    namespace: Annotated[
        list[str],
        Field(
            description="Namespace as [stage, entity_type] to search within, e.g. ['discovery', 'source'].",
        ),
    ],
    query: Annotated[
        str | None,
        Field(
            description="Semantic search text matched against source name and description. Optional.",
        ),
    ] = None,
    filter: Annotated[
        dict | None,
        Field(
            description=(
                "Metadata filter for exact-match filtering, e.g. "
                "{'source_type': 'paper'}, {'entity_name': 'market'}, "
                "or {'tier': 1}. Optional."
            ),
        ),
    ] = None,
    limit: Annotated[
        int,
        Field(
            description="Maximum number of results to return. Defaults to 10.",
        ),
    ] = 10,
) -> ToolResult:
    try:
        with StoreAdapter(DATABASE_URI, EMBEDDING_CONFIG) as adapter:
            repo = SourceRepo(adapter)
            results = repo.search(tuple(namespace), query=query, filter=filter, limit=limit)
            data = [s.as_dict() for s in results]
            return tool_result_list(data)
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc


@mcp.tool(
    name="remove",
    description=(
        "Removes a source profile from the store.\n\n"
        "Expects 'namespace' as [stage, entity_type] (e.g. ['discovery', "
        "'source']) and 'key' as the source 'id' identifying the source "
        "to remove.\n\n"
        "Produces {'status': 'ok', 'key': '<id>'} on success. Raises an "
        "error if no source exists with that key.\n\n"
        "Use this tool to delete a source that is no longer relevant. "
        "This does not cascade to signals or documents sourced from it."
    ),
)
def remove(
    namespace: Annotated[
        list[str],
        Field(
            description="Source namespace as [stage, entity_type], e.g. ['discovery', 'source'].",
        ),
    ],
    key: Annotated[
        str,
        Field(
            description="The source 'id' to remove.",
        ),
    ],
) -> ToolResult:
    try:
        with StoreAdapter(DATABASE_URI, EMBEDDING_CONFIG) as adapter:
            repo = SourceRepo(adapter)
            source = repo.get(tuple(namespace), key)
            if source is None:
                raise ToolError(f"Source not found: namespace={namespace}, key={key!r}")
            repo.remove(source)
            return tool_result_single({"status": "ok", "key": key})
    except ToolError:
        raise
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc


@mcp.tool(
    name="add",
    description=(
        "Persists a new source profile in the store.\n\n"
        "Expects a dict with required keys: 'name' (str), "
        "'description' (str), 'url' (str, canonical URL; normalized on "
        "ingest), 'source_type' (str: 'paper', 'publication', 'website', "
        "'blog', 'news', or 'social_media'), 'entity_name' (str: "
        "'innovation' or 'market'), 'tier' (int 1-3, where 1 is highest "
        "priority and 3 is lowest), 'id' (str, used as the store key), "
        "'stage' (str: 'discovery', 'development', 'validation', or "
        "'strategy'), 'entity_type' (str, 'source'). Optional keys: 'agent_name', "
        "'created' (ISO datetime str), 'modified' (ISO datetime str).\n\n"
        "Produces {'status': 'ok', 'key': '<id>'} on success. Raises "
        "an error if a source with the same key already exists.\n\n"
        "Use this tool to register a new research source that agents "
        "will query during discovery cycles."
    ),
)
def add(
    source_data: Annotated[
        dict,
        Field(
            description=(
                "Serialized source profile. Required keys: 'name', "
                "'description', 'url', 'source_type' (paper|publication|"
                "website|blog|news|social_media), 'entity_name' "
                "(innovation|market), 'tier' (int 1-3), 'id', 'stage', "
                "'entity_type'. Optional: 'agent_name', 'created' (ISO datetime str), "
                "'modified' (ISO datetime str)."
            ),
        ),
    ],
) -> ToolResult:
    try:
        with StoreAdapter(DATABASE_URI, EMBEDDING_CONFIG) as adapter:
            repo = SourceRepo(adapter)
            source = repo.deserialize(source_data)
            repo.add(source)
            return tool_result_single({"status": "ok", "key": source.key})
    except (ValueError, KeyError) as exc:
        raise ToolError(f"Invalid input: {exc}") from exc
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc


@mcp.tool(
    name="add_batch",
    description=(
        "Persists multiple source profiles in a single call.\n\n"
        "Expects a list of dicts, each following the add schema. "
        "Duplicates are skipped and counted as failures.\n\n"
        "Produces {'status': 'ok', 'succeeded': <int>, 'failed': <int>}.\n\n"
        "Use this tool to register multiple research sources at once, "
        "for example when bootstrapping a new discovery dimension."
    ),
)
def add_batch(
    sources_data: Annotated[
        list[dict],
        Field(
            description="List of serialized source dicts, each following the add schema.",
        ),
    ],
) -> ToolResult:
    try:
        with StoreAdapter(DATABASE_URI, EMBEDDING_CONFIG) as adapter:
            repo = SourceRepo(adapter)
            sources = repo.deserialize_batch(sources_data)
            result = repo.add_batch(sources)
            return tool_result_single(
                {
                    "status": "ok",
                    "succeeded": result.nsuccesses,
                    "failed": len(result.failed),
                }
            )
    except (ValueError, KeyError) as exc:
        raise ToolError(f"Invalid input: {exc}") from exc
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc


@mcp.tool(
    name="upsert",
    description=(
        "Creates or overwrites a source profile in the store.\n\n"
        "Expects a dict following the same schema as add. If a "
        "source with the same 'id' already exists in the namespace, it is "
        "overwritten with the new data. The 'modified' timestamp is set "
        "automatically to the current time.\n\n"
        "Produces {'status': 'ok', 'key': '<id>'}.\n\n"
        "Use this tool when an agent has revised a source profile "
        "(adjusting its description, source_type, entity_name, or tier) "
        "and needs to persist the change. Unlike add, this will "
        "not fail on existing sources."
    ),
)
def upsert(
    source_data: Annotated[
        dict,
        Field(
            description=(
                "Serialized source profile. Same schema as add. "
                "The 'modified' timestamp is set automatically and does not "
                "need to be included."
            ),
        ),
    ],
) -> ToolResult:
    try:
        with StoreAdapter(DATABASE_URI, EMBEDDING_CONFIG) as adapter:
            repo = SourceRepo(adapter)
            source = repo.deserialize(source_data)
            source.modified = datetime.now()
            repo.upsert(source)
            return tool_result_single({"status": "ok", "key": source.key})
    except (ValueError, KeyError) as exc:
        raise ToolError(f"Invalid input: {exc}") from exc
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc
