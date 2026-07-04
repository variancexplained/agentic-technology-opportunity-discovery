#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/tools/arxiv                                                                 #
# Filename   : arxiv.py                                                                            #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Sunday May 31st 2026                                                                #
# Modified   : Saturday June 27th 2026 06:34:04 am                                                 #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
"""MCP server for the arXiv discovery service of the Sciven pipeline."""

from __future__ import annotations

import logging
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.tools import ToolResult
from pydantic import Field

from sciven.application.discover.curate.arxiv import ArxivSearchRequest
from sciven.infra.web_search.arxiv.adapter import ArxivAdapter, ArxivError
from sciven.utils.tools import tool_result_list, tool_result_single

# ------------------------------------------------------------------------------------------------ #
logger = logging.getLogger(__name__)

# ruff: noqa: D103
# ------------------------------------------------------------------------------------------------ #
#                                             MCP                                                  #
# ------------------------------------------------------------------------------------------------ #
mcp = FastMCP("sciven-search-arxiv")


# ================================================================================================ #
#                                       ARXIV TOOLS                                                #
# ================================================================================================ #
#                                     ARXIV SEARCH TOOL                                            #
# ------------------------------------------------------------------------------------------------ #
@mcp.tool(
    name="search",
    description=(
        "Searches the live arXiv API and returns the matching papers. "
        "Expects 'request' as a serialized ArxivSearchRequest dict, built by the "
        "caller (e.g. with ArxivSearchRequestBuilder) and serialized via 'as_dict()'. "
        "It is the full request object the adapter fetches and records, including its "
        "'url' and its query, paging, and sort fields. "
        "'run_id' and 'agent_name' record the pipeline run and the calling agent on every returned paper. "
        "Returns a list of serialized ResearchPaper dicts (id, title, abstract, "
        "authors, url, name, source_id, run_id, search_id, agent_name, entity_name, "
        "document_format, published, updated). The papers are fetched and mapped but "
        "not persisted; pass them to the document server's add tools to store them. "
        "Use this tool to run a prepared arXiv query for a research run."
    ),
)
def search(
    run_id: Annotated[str, Field(description="Identifier of the current pipeline run.")],
    agent_name: Annotated[
        str,
        Field(description="Name of the calling agent, recorded as the agent_name on every paper."),
    ],
    request: Annotated[
        dict,
        Field(
            description=(
                "Serialized ArxivSearchRequest dict (from ArxivSearchRequest.as_dict()): the "
                "full request object, including the 'url' the adapter fetches and the query, "
                "paging, and sort fields."
            ),
        ),
    ],
) -> ToolResult:
    try:
        search_request = ArxivSearchRequest.create(request)
        adapter = ArxivAdapter(run_id=run_id, agent_name=agent_name)
        search, results = adapter.search(search_request)
        return tool_result_single(
            {
                "search": search.as_dict(),
                "results": [result.as_dict() for result in results],
            }
        )
    except (KeyError, ValueError, ArxivError) as exc:
        raise ToolError(str(exc)) from exc
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc


# ------------------------------------------------------------------------------------------------ #
#                                      ARXIV GET TOOL                                              #
# ------------------------------------------------------------------------------------------------ #
@mcp.tool(
    name="get",
    description=(
        "Resolves specific arXiv papers by identifier from the live arXiv API. "
        "Expects 'ids' as a list of arXiv identifiers (version suffix optional, e.g. "
        "'2512.23010v2'). 'run_id', 'source_id', and 'agent_name' record the pipeline "
        "run, the parent arXiv Source, and the calling agent on every returned paper. "
        "Returns a list of serialized ResearchPaper dicts, one per identifier that "
        "resolves; empty when none resolve. The papers are fetched and mapped but not "
        "persisted. Use this tool to fetch the canonical metadata for arXiv ids you "
        "already know."
    ),
)
def get(
    run_id: Annotated[str, Field(description="Identifier of the current pipeline run.")],
    agent_name: Annotated[
        str,
        Field(description="Name of the calling agent, recorded as the agent_name on every paper."),
    ],
    ids: Annotated[
        list[str], Field(description="arXiv identifiers to resolve, version suffix optional.")
    ],
) -> ToolResult:
    try:
        adapter = ArxivAdapter(run_id=run_id, agent_name=agent_name)
        papers = adapter.get(ids)
        return tool_result_list([paper.as_dict() for paper in papers])
    except ArxivError as exc:
        raise ToolError(str(exc)) from exc
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc
