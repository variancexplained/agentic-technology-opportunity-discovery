#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/services/signal                                                             #
# Filename   : signal.py                                                                           #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Monday April 20th 2026                                                              #
# Modified   : Wednesday July 1st 2026 05:06:14 pm                                                 #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
"""MCP server for the Signal service of the Sciven pipeline."""

from __future__ import annotations

import logging
from typing import Annotated

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.tools import ToolResult
from pydantic import Field

from sciven.harness.tools import DATABASE_URI, EMBEDDING_CONFIG, set_embedding_config
from sciven.infra.persistence.provider.langgraph.store import StoreAdapter
from sciven.infra.persistence.repo.signal import SignalRepo
from sciven.utils.tools import tool_result_list, tool_result_single

# ------------------------------------------------------------------------------------------------ #
logger = logging.getLogger(__name__)
load_dotenv()
# ruff: noqa: D103
# ------------------------------------------------------------------------------------------------ #

# ------------------------------------------------------------------------------------------------ #
#                                             MCP                                                  #
# ------------------------------------------------------------------------------------------------ #
set_embedding_config()  # Ensure embedding config is initialized before any repos or tools are used
mcp = FastMCP("sciven-signal")


# ================================================================================================ #
#                                     SIGNAL TOOLS                                                 #
# ================================================================================================ #
@mcp.tool(
    name="get",
    description=(
        "Retrieves a single signal by namespace and key. "
        "Expects 'namespace' as a list of strings representing the storage "
        "partition (e.g. ['research', 'innovation_signal', 'innovation', "
        "'cost_collapse']), and 'key' as the signal name slug. "
        "Produces the full serialized signal dict on success, or null if "
        "no signal exists with that key. "
        "Use this tool to look up a specific signal by its key, for "
        "example to inspect its score, document, or metadata."
    ),
)
def get(
    namespace: Annotated[
        list[str],
        Field(
            description=("Signal namespace path, e.g. ['discovery', 'signal']."),
        ),
    ],
    key: Annotated[
        str,
        Field(
            description="The signal name slug used as the storage key.",
        ),
    ],
) -> ToolResult:
    try:
        with StoreAdapter(DATABASE_URI, EMBEDDING_CONFIG) as adapter:
            repo = SignalRepo(adapter)
            signal = repo.get(tuple(namespace), key)
            if signal is None:
                return tool_result_single(None)
            return tool_result_single(signal.as_dict())
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc


@mcp.tool(
    name="search",
    description=(
        "Searches signals within a namespace using optional semantic "
        "text and metadata filters. "
        "Expects 'namespace' as a list of strings defining the search scope "
        "(e.g. ['research', 'innovation_signal', 'innovation', 'cost_collapse'] to search "
        "all innovation signals). Optional 'query' performs semantic "
        "similarity against signal name and description. Optional 'filter' "
        "matches exact values on stored fields "
        "(e.g. {'source_url': 'https://...'}). 'limit' caps results "
        "(default 10). "
        "Produces a list of serialized signal dicts ranked by relevance. "
        "Use this tool to find signals matching a research topic, to "
        "check for duplicates before adding, or to retrieve all signals "
        "within a dimension."
    ),
)
def search(
    namespace: Annotated[
        list[str],
        Field(
            description=(
                "Namespace prefix to search within, e.g. "
                "['research', 'innovation_signal', 'innovation', 'cost_collapse']."
            ),
        ),
    ],
    query: Annotated[
        str | None,
        Field(
            description=(
                "Semantic search text matched against signal name and description. Optional."
            ),
        ),
    ] = None,
    filter: Annotated[
        dict | None,
        Field(
            description=(
                "Metadata filter for exact-match filtering, "
                "e.g. {'source_url': 'https://...'}. Optional."
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
            repo = SignalRepo(adapter)
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


@mcp.tool(
    name="add",
    description=(
        "Creates a new signal in the store. "
        "Expects a 'data' dict following the Signal schema. Required "
        "fields: name, description, representation, phenomenon, "
        "interpretation, dimension, impact_magnitude, "
        "discontinuity_category, discontinuity_claim, impact_quantitative, "
        "score (dict with novelty, magnitude, economic, autonomy, "
        "evidence, generality), document (dict with author, url, title, "
        "publication, date). The dimension value determines "
        "the concrete signal subclass (innovation, capital_flow, markets, "
        "behavioral, economics). "
        "The signal is checked against four-tier deduplication (exact "
        "key, exact URL, exact title, semantic similarity) before "
        "insertion. Raises an error if a duplicate is detected. "
        "Produces {'status': 'ok', 'key': '<signal_name>'} on success. "
        "Use this tool to persist a newly discovered signal from a "
        "research cycle."
    ),
)
def add(
    data: Annotated[
        dict,
        Field(
            description=(
                "Signal payload dict. Must include: name, description, "
                "representation, phenomenon, interpretation, "
                "dimension, impact_magnitude, discontinuity_category, discontinuity_claim, "
                "impact_quantitative, score, document. "
                "Optional fields: signal_date, "
                "adoption, behavioral, market_segment, market_vertical, "
                "market_horizontal, market_consumer, market_prosumer, "
                "market_size_estimate, market_demand, market_competition, "
                "capital_investors, capital_rationale, capital_deal_amount, "
                "capital_valuation, economic_key_indicators, labor_impacts, "
                "economic_business_impacts, economic_wealth_effects, "
                "time_horizon, tags."
            ),
        ),
    ],
) -> ToolResult:
    try:
        with StoreAdapter(DATABASE_URI, EMBEDDING_CONFIG) as adapter:
            repo = SignalRepo(adapter)
            signal = repo.deserialize(data)
            repo.add(signal)
            return tool_result_single({"status": "ok", "key": signal.key})
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc


@mcp.tool(
    name="add_batch",
    description=(
        "Creates multiple signals in a single operation. "
        "Expects 'items' as a list of signal payload dicts, each "
        "following the same schema as add. Each signal is "
        "independently deserialized and checked for duplicates. "
        "Duplicates are skipped (not inserted) and reported in the "
        "result rather than raising an error. "
        "Produces {'nsuccesses': <int>, 'nfailed': <int>, "
        "'failed_keys': [<str>, ...]} summarizing the batch outcome. "
        "Use this tool to persist multiple signals from a research "
        "cycle in one call, avoiding the overhead of individual "
        "add calls."
    ),
)
def add_batch(
    items: Annotated[
        list[dict],
        Field(
            description="List of signal payload dicts to add.",
        ),
    ],
) -> ToolResult:
    try:
        with StoreAdapter(DATABASE_URI, EMBEDDING_CONFIG) as adapter:
            repo = SignalRepo(adapter)
            signals = repo.deserialize_batch(items)
            result = repo.add_batch(signals)
            return tool_result_single(
                {
                    "nsuccesses": result.nsuccesses,
                    "nfailed": len(result.failed),
                    "failed_keys": [s.key for s in result.failed],
                }
            )
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc


@mcp.tool(
    name="remove",
    description=(
        "Removes a signal from the store. "
        "Expects 'namespace' and 'key' identifying the signal to remove. "
        "Produces {'status': 'ok', 'key': '<key>'} on success. Raises an "
        "error if no signal exists with that key. "
        "Use this tool to delete a signal that was added in error or is "
        "no longer relevant."
    ),
)
def remove(
    namespace: Annotated[
        list[str],
        Field(
            description=(
                "Signal namespace path, e.g. "
                "['research', 'innovation_signal', 'innovation', 'cost_collapse']."
            ),
        ),
    ],
    key: Annotated[
        str,
        Field(
            description="The signal name slug to remove.",
        ),
    ],
) -> ToolResult:
    try:
        with StoreAdapter(DATABASE_URI, EMBEDDING_CONFIG) as adapter:
            repo = SignalRepo(adapter)
            signal = repo.get(tuple(namespace), key)
            if signal is None:
                raise ToolError(f"Signal not found: namespace={namespace}, key={key!r}")
            repo.remove(signal)
            return tool_result_single({"status": "ok", "key": key})
    except ToolError:
        raise
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc
