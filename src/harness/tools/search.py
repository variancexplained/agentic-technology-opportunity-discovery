#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/tools/search                                                                #
# Filename   : search.py                                                                           #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Wednesday June 3rd 2026 09:10:00 pm                                                 #
# Modified   : Monday June 29th 2026 06:49:34 am                                                   #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
"""MCP server for the Search service of the Sciven pipeline."""

from __future__ import annotations

import logging
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.tools import ToolResult
from pydantic import Field

from sciven.harness.tools import DATABASE_URI, EMBEDDING_CONFIG, set_embedding_config
from sciven.infra.persistence.provider.langgraph.store import StoreAdapter
from sciven.infra.persistence.repo.search import SearchRepo
from sciven.utils.tools import tool_result_list, tool_result_single

# ------------------------------------------------------------------------------------------------ #
logger = logging.getLogger(__name__)

# ruff: noqa: D103
# ------------------------------------------------------------------------------------------------ #

# ------------------------------------------------------------------------------------------------ #
#                                             MCP                                                  #
# ------------------------------------------------------------------------------------------------ #
set_embedding_config()  # Ensure embedding config is initialized before any repos or tools are used
mcp = FastMCP("sciven-search")


# ================================================================================================ #
#                                      SEARCH TOOLS                                                #
# ================================================================================================ #
#                                     SEARCH GET TOOL                                              #
# ------------------------------------------------------------------------------------------------ #
@mcp.tool(
    name="get",
    description=(
        "Retrieves a single search transaction by namespace and key. "
        "Expects 'namespace' as ['discovery', 'search'] and 'key' as "
        "the search's id. "
        "Returns the full serialized search dict (including api, request, "
        "result, run_id, source_id, agent_name, stage, entity_type, created, "
        "and modified fields) on success, or null if no search exists with "
        "that key. "
        "Use this tool to look up a specific search transaction by its id."
    ),
)
def get(
    namespace: Annotated[
        list[str],
        Field(
            description=("Search namespace path. Always ['discovery', 'search']."),
        ),
    ],
    key: Annotated[
        str,
        Field(
            description="The search's id used as the storage key.",
        ),
    ],
) -> ToolResult:
    try:
        with StoreAdapter(DATABASE_URI, EMBEDDING_CONFIG) as adapter:
            repo = SearchRepo(adapter)
            search = repo.get(tuple(namespace), key)
            if search is None:
                return tool_result_single(None)
            return tool_result_single(search.as_dict())
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc


# ------------------------------------------------------------------------------------------------ #
#                                    SEARCH SEARCH TOOL                                            #
# ------------------------------------------------------------------------------------------------ #
@mcp.tool(
    name="search",
    description=(
        "Searches search transactions within the search namespace using "
        "optional semantic text and metadata filters. "
        "Expects 'namespace' as ['discovery', 'search']. Optional 'query' "
        "performs semantic similarity against the search's embedding text "
        "(the request URL and result title). Optional 'filter' matches exact "
        "values on stored fields (common filters: 'api', 'source_id', "
        "'run_id'). "
        "'limit' caps results (default 10). "
        "Returns a list of serialized search dicts ranked by relevance. "
        "Use this tool to find prior searches for a source or run, or to "
        "check whether a query has already been executed."
    ),
)
def search(
    namespace: Annotated[
        list[str],
        Field(
            description=("Namespace prefix to search within. Always ['discovery', 'search']."),
        ),
    ],
    query: Annotated[
        str | None,
        Field(
            description=(
                "Semantic search text matched against the search's request URL and result "
                "title. Optional."
            ),
        ),
    ] = None,
    filter: Annotated[
        dict | None,
        Field(
            description=(
                "Metadata filter for exact-match filtering against stored "
                "fields, e.g. {'api': 'arxiv'}, {'source_id': '...'}, "
                "{'run_id': '...'}. Optional."
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
            repo = SearchRepo(adapter)
            results = repo.search(
                tuple(namespace),
                query=query,
                filter=filter,
                limit=limit,
            )
            data = [s.as_dict() for s in results]
            return tool_result_list(data)
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc


# ------------------------------------------------------------------------------------------------ #
#                                    SEARCH ADD TOOL                                               #
# ------------------------------------------------------------------------------------------------ #
@mcp.tool(
    name="add",
    description=(
        "Creates a new search transaction in the store. "
        "Expects a 'data' dict following the serialized Search schema. "
        "Required fields: api (one of 'arxiv'), id, request (a serialized "
        "request dict carrying the query fields and URL), result (a "
        "serialized result dict carrying the feed title and counts), "
        "stage ('discovery'), entity_type ('search'), run_id, source_id "
        "(string id of the parent Source), agent_name, and created (ISO 8601 "
        "datetime). Optional field: modified (ISO 8601 datetime or null). "
        "The search is rejected if its key already exists in the namespace. "
        "Returns {'status': 'ok', 'key': '<id>'} on success. "
        "Use this tool to persist a completed search transaction surfaced "
        "from an adapter such as the arXiv search server."
    ),
)
def add(
    data: Annotated[
        dict,
        Field(
            description=(
                "Search payload dict. Required: api, id, request, result, "
                "stage, entity_type, run_id, source_id, agent_name, created. "
                "Optional: modified."
            ),
        ),
    ],
) -> ToolResult:
    try:
        with StoreAdapter(DATABASE_URI, EMBEDDING_CONFIG) as adapter:
            repo = SearchRepo(adapter)
            search = repo.deserialize(data)
            repo.add(search)
            return tool_result_single({"status": "ok", "key": search.key})
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc


# ------------------------------------------------------------------------------------------------ #
#                                    SEARCH ADD BATCH TOOL                                         #
# ------------------------------------------------------------------------------------------------ #
@mcp.tool(
    name="add_batch",
    description=(
        "Creates multiple search transactions in a single operation. "
        "Expects 'items' as a list of search payload dicts, each following "
        "the same schema as add. Each search is independently "
        "deserialized and checked for a duplicate key. Duplicates and "
        "malformed payloads are skipped (not inserted) and reported in the "
        "result rather than raising an error. "
        "Returns {'nsuccesses': <int>, 'nfailed': <int>, "
        "'failed_keys': [<str>, ...]} summarizing the batch outcome. "
        "Use this tool to persist many search transactions from a single "
        "research cycle in one call, avoiding the overhead of individual "
        "add calls."
    ),
)
def add_batch(
    items: Annotated[
        list[dict],
        Field(
            description="List of search payload dicts to add.",
        ),
    ],
) -> ToolResult:
    try:
        with StoreAdapter(DATABASE_URI, EMBEDDING_CONFIG) as adapter:
            repo = SearchRepo(adapter)
            searches = repo.deserialize_batch(items)
            result = repo.add_batch(searches)
            return tool_result_single(
                {
                    "nsuccesses": result.nsuccesses,
                    "nfailed": len(result.failed),
                    "failed_keys": [s.key for s in result.failed],
                }
            )
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc


# ------------------------------------------------------------------------------------------------ #
#                                    SEARCH REMOVE TOOL                                            #
# ------------------------------------------------------------------------------------------------ #
@mcp.tool(
    name="remove",
    description=(
        "Removes a search transaction from the store. "
        "Expects 'namespace' as ['discovery', 'search'] and 'key' as the "
        "search's id to remove. "
        "Returns {'status': 'ok', 'key': '<key>'} on success. Raises an "
        "error if no search exists with that key. "
        "Use this tool to delete a search that was recorded in error or has "
        "been superseded."
    ),
)
def remove(
    namespace: Annotated[
        list[str],
        Field(
            description=("Search namespace path. Always ['discovery', 'search']."),
        ),
    ],
    key: Annotated[
        str,
        Field(
            description="The search's id to remove.",
        ),
    ],
) -> ToolResult:
    try:
        with StoreAdapter(DATABASE_URI, EMBEDDING_CONFIG) as adapter:
            repo = SearchRepo(adapter)
            search = repo.get(tuple(namespace), key)
            if search is None:
                raise ToolError(f"Search not found: namespace={namespace}, key={key!r}")
            repo.remove(search)
            return tool_result_single({"status": "ok", "key": key})
    except ToolError:
        raise
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc
