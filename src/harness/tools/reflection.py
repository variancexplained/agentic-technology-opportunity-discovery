#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/services/source                                                             #
# Filename   : reflection.py                                                                       #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Monday April 20th 2026                                                              #
# Modified   : Monday June 29th 2026 06:49:35 am                                                   #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
"""MCP server for the Source stage of the Sciven pipeline."""

from __future__ import annotations

import logging
from typing import Annotated

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.tools import ToolResult
from pydantic import Field

from sciven.domain import EntityType, Stage, TaskType
from sciven.domain.core import EntityName
from sciven.harness.tools import DATABASE_URI, EMBEDDING_CONFIG, set_embedding_config
from sciven.infra.persistence.provider.langgraph.store import StoreAdapter
from sciven.infra.persistence.repo.reflection import ReflectionRepo
from sciven.utils.tools import tool_result_list, tool_result_single

# ------------------------------------------------------------------------------------------------ #
logger = logging.getLogger(__name__)
load_dotenv()
# ruff: noqa: D103
# ------------------------------------------------------------------------------------------------ #
#                                            MCP                                                   #
# ------------------------------------------------------------------------------------------------ #
mcp = FastMCP("sciven-reflections")
set_embedding_config()  # Load embedding config on startup


# ================================================================================================ #
#                                   REFLECTION TOOLS                                               #
# ================================================================================================ #
@mcp.tool(
    name="add",
    description=(
        "Persists a reflection capturing a process lesson or observation from the source stage."
        "Expects a dict with required keys: 'stage' (str, e.g. 'source'), "
        "'entity_type' (str), 'name' (str, short title), 'content' (str, the "
        "lesson text), 'importance' (int 1-5), 'confidence' (float 0-1). "
        "Optional keys: 'dimension', 'impact_magnitude', "
        "'discontinuity_category', 'market_segment', 'market_vertical', "
        "'market_horizontal', 'market_consumer', 'market_prosumer', "
        "'id' (auto-generated if omitted), 'created' (defaults to now).\n\n"
        "Produces {'status': 'ok', 'key': '<n>'} on success. Raises "
        "an error if a reflection with the same name already exists.\n\n"
        "Use this tool after completing a source-processing cycle to "
        "record what worked, what failed, and what to adjust next time. "
        "These reflections are retrieved by future runs to improve "
        "search strategy."
    ),
)
def add(
    reflection_data: Annotated[
        dict,
        Field(
            description=(
                "Serialized reflection. Required keys: 'stage' (str), 'entity_type' "
                "(str), 'name' (str), 'content' (str), 'importance' (int 1-5), "
                "'confidence' (float 0-1). Optional: 'dimension', "
                "'impact_magnitude', 'discontinuity_category', 'market_segment', "
                "'market_vertical', 'market_horizontal', 'market_consumer', "
                "'market_prosumer', 'id' (str), 'created' (ISO datetime str)."
            ),
        ),
    ],
) -> ToolResult:
    try:
        with StoreAdapter(DATABASE_URI, EMBEDDING_CONFIG) as adapter:
            repo = ReflectionRepo(adapter)
            reflection = repo.deserialize(reflection_data)
            repo.add(reflection)
            return tool_result_single({"status": "ok", "key": reflection.key})
    except (ValueError, KeyError) as exc:
        raise ToolError(f"Invalid input: {exc}") from exc
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc


@mcp.tool(
    name="add_batch",
    description=(
        "Persists multiple reflections in a single call.\n\n"
        "Expects a list of dicts, each following the add schema. "
        "Duplicates are skipped and counted as failures.\n\n"
        "Produces {'status': 'ok', 'succeeded': <int>, 'failed': <int>}.\n\n"
        "Use this tool when a processing run generates several lessons at "
        "once, rather than calling add repeatedly."
    ),
)
def add_batch(
    reflections_data: Annotated[
        list[dict],
        Field(
            description="List of serialized reflection dicts, each following the add schema.",
        ),
    ],
) -> ToolResult:
    try:
        with StoreAdapter(DATABASE_URI, EMBEDDING_CONFIG) as adapter:
            repo = ReflectionRepo(adapter)
            reflections = repo.deserialize_batch(reflections_data)
            result = repo.add_batch(reflections)
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
    name="get",
    description=(
        "Retrieves a single reflection by namespace and key.\n\n"
        "Expects 'namespace' as a list of strings and 'key' as the "
        "reflection name.\n\n"
        "Produces the full serialized reflection dict, or null if not "
        "found.\n\n"
        "Use this tool to look up a specific reflection by name."
    ),
)
def get(
    namespace: Annotated[
        list[str],
        Field(
            description="Reflection namespace path as a list of strings.",
        ),
    ],
    key: Annotated[
        str,
        Field(
            description="The reflection name used as the store key.",
        ),
    ],
) -> ToolResult:
    try:
        with StoreAdapter(DATABASE_URI, EMBEDDING_CONFIG) as adapter:
            repo = ReflectionRepo(adapter)
            reflection = repo.get(tuple(namespace), key)
            if reflection is None:
                return tool_result_single(None)
            return tool_result_single(reflection.as_dict())
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc


@mcp.tool(
    name="search",
    description=(
        "Searches reflections within a (stage, entity_type) namespace using "
        "optional semantic text and metadata filters.\n\n"
        "Requires 'stage' and 'entity_type' (enum value strings), which "
        "together define the namespace to search within. Optional "
        "'agent_name', 'subject', 'task_type', and 'entity_name' narrow the "
        "results via exact metadata matching; each non-null value is added to "
        "the filter. Optional 'query' performs semantic similarity against "
        "reflection name and content. 'limit' caps results (default 10).\n\n"
        "Results are sorted according to 'sort_by'. The default "
        "'relevance' preserves the adapter's semantic-similarity ranking. "
        "Set sort_by='recency' to rank by exponential time-decay score, "
        "or use any other Reflection field name (e.g. 'created'). "
        "'sort_reverse' controls ascending (False) vs descending (True) "
        "order and defaults to True (most relevant / most recent first).\n\n"
        "Produces a list of serialized reflection dicts.\n\n"
        "Use this tool at the start of a processing run to retrieve "
        "lessons from prior runs that apply to the current dimension "
        "or stage."
    ),
)
def search(
    stage: Annotated[
        str,
        Field(
            description="Pipeline stage value (e.g. 'discovery'). First element of the namespace.",
        ),
    ],
    entity_type: Annotated[
        str,
        Field(
            description=("Entity type value (e.g. 'reflection'). Second element of the namespace."),
        ),
    ],
    agent_name: Annotated[
        str | None,
        Field(
            description="Filter to reflections produced by this agent name. Optional.",
        ),
    ] = None,
    subject: Annotated[
        str | None,
        Field(
            description="Filter by subject entity type value (e.g. 'signal'). Optional.",
        ),
    ] = None,
    task_type: Annotated[
        str | None,
        Field(
            description="Filter by task type value. Optional.",
        ),
    ] = None,
    entity_name: Annotated[
        str | None,
        Field(
            description="Filter by entity name value. Optional.",
        ),
    ] = None,
    query: Annotated[
        str | None,
        Field(
            description="Semantic search text matched against reflection name and content. Optional.",
        ),
    ] = None,
    limit: Annotated[
        int,
        Field(
            description="Maximum number of results to return. Defaults to 10.",
        ),
    ] = 10,
    sort_by: Annotated[
        str,
        Field(
            description=(
                "Field to sort results by. 'relevance' (default) preserves the "
                "adapter's semantic-similarity order. 'recency' sorts by exponential "
                "time-decay score. Any other Reflection field name (e.g. 'created') "
                "is also accepted."
            ),
        ),
    ] = "relevance",
    sort_reverse: Annotated[
        bool,
        Field(
            description=(
                "Sort direction. True (default) returns highest values first "
                "(most relevant or most recent). False returns lowest first."
            ),
        ),
    ] = True,
) -> ToolResult:
    try:
        namespace = (
            Stage.from_value(stage).value,
            EntityType.from_value(entity_type).value,
        )
        filter = {}
        if agent_name is not None:
            filter["agent_name"] = agent_name
        if subject is not None:
            filter["subject"] = EntityType.from_value(subject).value
        if task_type is not None:
            filter["task_type"] = TaskType.from_value(task_type).value
        if entity_name is not None:
            filter["entity_name"] = EntityName.from_value(entity_name).value
    except (ValueError, KeyError) as exc:
        raise ToolError(f"Invalid input: {exc}") from exc

    try:
        with StoreAdapter(DATABASE_URI, EMBEDDING_CONFIG) as adapter:
            repo = ReflectionRepo(adapter)
            results = repo.search(
                namespace,
                query=query,
                filter=filter or None,
                limit=limit,
                sort_by=sort_by,
                sort_reverse=sort_reverse,
            )
            data = [r.as_dict() for r in results]
            return tool_result_list(data)
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc


@mcp.tool(
    name="remove",
    description=(
        "Removes a reflection from the store.\n\n"
        "Expects 'namespace' and 'key' identifying the reflection.\n\n"
        "Produces {'status': 'ok', 'key': '<key>'} on success. Raises "
        "an error if no reflection exists with that key.\n\n"
        "Use this tool to retire outdated process lessons that no longer "
        "apply."
    ),
)
def remove(
    namespace: Annotated[
        list[str],
        Field(
            description="Reflection namespace path.",
        ),
    ],
    key: Annotated[
        str,
        Field(
            description="The reflection name (key) to remove.",
        ),
    ],
) -> ToolResult:
    try:
        with StoreAdapter(DATABASE_URI, EMBEDDING_CONFIG) as adapter:
            repo = ReflectionRepo(adapter)
            reflection = repo.get(tuple(namespace), key)
            if reflection is None:
                raise ToolError(f"Reflection not found: namespace={namespace}, key={key!r}")
            repo.remove(reflection)
            return tool_result_single({"status": "ok", "key": key})
    except ToolError:
        raise
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc
