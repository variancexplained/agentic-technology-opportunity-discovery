#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/tools/document                                                              #
# Filename   : document.py                                                                         #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Monday April 20th 2026                                                              #
# Modified   : Monday June 29th 2026 06:49:29 am                                                   #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
"""MCP server for the Document service of the Sciven pipeline."""

from __future__ import annotations

import logging
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.tools import ToolResult
from pydantic import Field

from sciven.harness.tools import DATABASE_URI, EMBEDDING_CONFIG, set_embedding_config
from sciven.infra.persistence.provider.langgraph.store import StoreAdapter
from sciven.infra.persistence.repo.document import DocumentRepo
from sciven.utils.tools import tool_result_list, tool_result_single

# ------------------------------------------------------------------------------------------------ #
logger = logging.getLogger(__name__)

# ruff: noqa: D103
# ------------------------------------------------------------------------------------------------ #

# ------------------------------------------------------------------------------------------------ #
#                                             MCP                                                  #
# ------------------------------------------------------------------------------------------------ #
set_embedding_config()  # Ensure embedding config is initialized before any repos or tools are used
mcp = FastMCP("sciven-document")


# ================================================================================================ #
#                                     DOCUMENT TOOLS                                               #
# ================================================================================================ #
#                                    DOCUMENT GET TOOL                                             #
# ------------------------------------------------------------------------------------------------ #
@mcp.tool(
    name="get",
    description=(
        "Retrieves a single document by namespace and key. "
        "Expects 'namespace' as ['discovery', 'document'] and 'key' as "
        "the document's id. "
        "Returns the full serialized document dict (including url, author, "
        "title, publication, abstract, source_id, entity_name, "
        "document_format, filepath, published, updated, "
        "and identity_type fields) on "
        "success, or null if no document exists with that key. "
        "Use this tool to look up a specific document by its id."
    ),
)
def get(
    namespace: Annotated[
        list[str],
        Field(
            description=("Document namespace path. Always ['discovery', 'document']."),
        ),
    ],
    key: Annotated[
        str,
        Field(
            description="The document's id used as the storage key.",
        ),
    ],
) -> ToolResult:
    try:
        with StoreAdapter(DATABASE_URI, EMBEDDING_CONFIG) as adapter:
            repo = DocumentRepo(adapter)
            document = repo.get(tuple(namespace), key)
            if document is None:
                return tool_result_single(None)
            return tool_result_single(document.as_dict())
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc


# ------------------------------------------------------------------------------------------------ #
#                                    DOCUMENT SEARCH TOOL                                          #
# ------------------------------------------------------------------------------------------------ #
@mcp.tool(
    name="search",
    description=(
        "Searches documents within the document namespace using optional "
        "semantic text and metadata filters. "
        "Expects 'namespace' as ['discovery', 'document']. Optional 'query' "
        "performs semantic similarity against the document's title and "
        "abstract. Optional 'filter' matches exact values on stored fields "
        "(common filters: 'entity_name', 'document_format', "
        "'publication', 'author', 'url', 'source_id')."
        "'limit' caps results (default 10). "
        "Returns a list of serialized document dicts ranked by relevance. "
        "Use this tool to find documents on a research topic, retrieve all "
        "documents of a given format or type, or check whether "
        "a URL has already been ingested."
    ),
)
def search(
    namespace: Annotated[
        list[str],
        Field(
            description=("Namespace prefix to search within. Always ['discovery', 'document']."),
        ),
    ],
    query: Annotated[
        str | None,
        Field(
            description=(
                "Semantic search text matched against the document's title and abstract. Optional."
            ),
        ),
    ] = None,
    filter: Annotated[
        dict | None,
        Field(
            description=(
                "Metadata filter for exact-match filtering against stored "
                "fields, e.g. {'entity_name': 'paper'}, "
                "{'document_format': 'pdf'}, "
                "{'url': 'https://...'}. Optional."
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
            repo = DocumentRepo(adapter)
            results = repo.search(
                tuple(namespace),
                query=query,
                filter=filter,
                limit=limit,
            )
            data = [d.as_dict() for d in results]
            return tool_result_list(data)
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc


# ------------------------------------------------------------------------------------------------ #
#                                  DOCUMENT SEARCH IDS TOOL                                        #
# ------------------------------------------------------------------------------------------------ #
@mcp.tool(
    name="search_ids",
    description=(
        "Searches documents within the document namespace using optional "
        "semantic text and metadata filters, returning only the matching "
        "document ids. "
        "Expects 'namespace' as ['discovery', 'document']. Optional 'query' "
        "performs semantic similarity against the document's title and "
        "abstract. Optional 'filter' matches exact values on stored fields "
        "(common filters: 'entity_name', 'document_format', "
        "'publication', 'author', 'url', 'source_id')."
        "'limit' caps results (default 10). "
        "Returns a list of document id strings ranked by relevance. "
        "Use this tool when you only need to identify or count matching "
        "documents (e.g. dedup checks, id collection) without the overhead "
        "of their full serialized payloads; use search when you "
        "need the document fields themselves."
    ),
)
def search_ids(
    namespace: Annotated[
        list[str],
        Field(
            description=("Namespace prefix to search within. Always ['discovery', 'document']."),
        ),
    ],
    query: Annotated[
        str | None,
        Field(
            description=(
                "Semantic search text matched against the document's title and abstract. Optional."
            ),
        ),
    ] = None,
    filter: Annotated[
        dict | None,
        Field(
            description=(
                "Metadata filter for exact-match filtering against stored "
                "fields, e.g. {'entity_name': 'paper'}, "
                "{'document_format': 'pdf'}, "
                "{'url': 'https://...'}. Optional."
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
            repo = DocumentRepo(adapter)
            results = repo.search(
                tuple(namespace),
                query=query,
                filter=filter,
                limit=limit,
            )
            return tool_result_list([d.key for d in results])
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc


# ------------------------------------------------------------------------------------------------ #
#                                    DOCUMENT ADD TOOL                                             #
# ------------------------------------------------------------------------------------------------ #
@mcp.tool(
    name="add",
    description=(
        "Creates a new document in the store. "
        "Expects a 'data' dict following the Document schema. Required "
        "fields: url, author, title, publication, abstract, source_id "
        "(string id of the parent Source), entity_name (one of "
        "'paper', 'blog', 'report', 'news', 'patent'), and "
        "document_format (one of 'pdf', 'html', 'markdown'). "
        "Optional fields:  filepath (local path to the document file), "
        "published (ISO 8601 datetime), updated (ISO 8601 datetime), "
        "id (optional; auto-generated from url, title, published, updated if omitted). "
        "The document is rejected via three-tier dedup if its key, "
        "normalized URL, or title already exists in the namespace. "
        "Returns {'status': 'ok', 'key': '<id>'} on success. "
        "Use this tool to persist a single document surfaced from a web "
        "search or fetch."
    ),
)
def add(
    data: Annotated[
        dict,
        Field(
            description=(
                "Document payload dict. Required: url, author, title, "
                "publication, abstract, source_id, entity_name, "
                "document_format. "
                "Optional: filepath, published, updated, "
                "id (optional; auto-generated from url, title, published, updated if omitted)."
            ),
        ),
    ],
) -> ToolResult:
    try:
        with StoreAdapter(DATABASE_URI, EMBEDDING_CONFIG) as adapter:
            repo = DocumentRepo(adapter)
            document = repo.deserialize(data)
            repo.add(document)
            return tool_result_single({"status": "ok", "key": document.key})
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc


# ------------------------------------------------------------------------------------------------ #
#                                    DOCUMENT ADD BATCH TOOL                                       #
# ------------------------------------------------------------------------------------------------ #
@mcp.tool(
    name="add_batch",
    description=(
        "Creates multiple documents in a single operation. "
        "Expects 'items' as a list of document payload dicts, each "
        "following the same schema as add. Each document is "
        "independently deserialized and checked via three-tier dedup "
        "(key, URL, title). Duplicates and malformed payloads are skipped "
        "(not inserted) and reported in the result rather than raising an "
        "error. "
        "Returns {'nsuccesses': <int>, 'nfailed': <int>, "
        "'failed_keys': [<str>, ...]} summarizing the batch outcome. "
        "Use this tool to persist many documents from a single research "
        "cycle in one call, avoiding the overhead of individual "
        "add calls."
    ),
)
def add_batch(
    items: Annotated[
        list[dict],
        Field(
            description="List of document payload dicts to add.",
        ),
    ],
) -> ToolResult:
    try:
        with StoreAdapter(DATABASE_URI, EMBEDDING_CONFIG) as adapter:
            repo = DocumentRepo(adapter)
            documents = repo.deserialize_batch(items)
            result = repo.add_batch(documents)
            return tool_result_single(
                {
                    "nsuccesses": result.nsuccesses,
                    "nfailed": len(result.failed),
                    "failed_keys": [d.key for d in result.failed],
                }
            )
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc


# ------------------------------------------------------------------------------------------------ #
#                                    DOCUMENT REMOVE TOOL                                          #
# ------------------------------------------------------------------------------------------------ #
@mcp.tool(
    name="remove",
    description=(
        "Removes a document from the store. "
        "Expects 'namespace' as ['discovery', 'document'] and 'key' as the "
        "document's id to remove. "
        "Returns {'status': 'ok', 'key': '<key>'} on success. Raises an "
        "error if no document exists with that key. "
        "Use this tool to delete a document that was added in error, is "
        "no longer reachable, or has been superseded."
    ),
)
def remove(
    namespace: Annotated[
        list[str],
        Field(
            description=("Document namespace path. Always ['discovery', 'document']."),
        ),
    ],
    key: Annotated[
        str,
        Field(
            description="The document's id to remove.",
        ),
    ],
) -> ToolResult:
    try:
        with StoreAdapter(DATABASE_URI, EMBEDDING_CONFIG) as adapter:
            repo = DocumentRepo(adapter)
            document = repo.get(tuple(namespace), key)
            if document is None:
                raise ToolError(f"Document not found: namespace={namespace}, key={key!r}")
            repo.remove(document)
            return tool_result_single({"status": "ok", "key": key})
    except ToolError:
        raise
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc
