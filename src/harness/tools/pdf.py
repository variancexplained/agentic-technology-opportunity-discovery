#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/tools/pdf                                                                   #
# Filename   : pdf.py                                                                              #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Monday June 1st 2026                                                                #
# Modified   : Wednesday June 3rd 2026 01:35:15 pm                                                 #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
"""MCP server for the PDF discovery service of the Sciven pipeline."""

from __future__ import annotations

import logging
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.tools import ToolResult
from pydantic import Field

from sciven.utils.pdf import PDFDownloadError, ResearchPDF, SectionNotFoundError
from sciven.utils.tools import tool_result_single

# ------------------------------------------------------------------------------------------------ #
logger = logging.getLogger(__name__)

# ruff: noqa: D103
# ------------------------------------------------------------------------------------------------ #
#                                      DOWNLOAD DEFAULTS                                           #
# ------------------------------------------------------------------------------------------------ #
DEFAULT_TIMEOUT: float = 30.0  # Per-request timeout, in seconds.
DEFAULT_MAX_BYTES: int = 50 * 1024 * 1024  # Reject downloads larger than 50 MiB.
DEFAULT_MAX_REDIRECTS: int = 5  # Maximum number of redirects to follow.

# ------------------------------------------------------------------------------------------------ #
#                                             MCP                                                  #
# ------------------------------------------------------------------------------------------------ #
mcp = FastMCP("sciven-pdf")


# ================================================================================================ #
#                                        PDF TOOLS                                                 #
# ================================================================================================ #
#                                     PDF DOWNLOAD TOOL                                            #
# ------------------------------------------------------------------------------------------------ #
@mcp.tool(
    name="pdf_download",
    description=(
        "Downloads a PDF over HTTP(S) to a local path and returns where it was saved. "
        "Fetches 'url' and writes it to 'filepath' (parent directories are created). "
        "The download is validated: the scheme must be http or https and, when "
        "'allowed_hosts' is given, the request host must be in that set on the original "
        "URL and on every redirect hop; the body must not exceed 'max_bytes'; and the "
        "'%PDF-' header must appear near the start, so an HTML error page is never saved "
        "as a PDF. 'timeout' is the per-request timeout in seconds (default 30); "
        "'max_redirects' caps the redirects followed (default 5). "
        "Returns {'status': 'ok', 'path': '<saved path>'}. "
        "Use this tool to fetch a research PDF (for example an arXiv paper's url) before "
        "reading it with pdf_list_sections and pdf_get_section."
    ),
)
def pdf_download(
    url: Annotated[str, Field(description="HTTP(S) URL of the PDF to download.")],
    filepath: Annotated[
        str, Field(description="Local destination path. Parent directories are created.")
    ],
    allowed_hosts: Annotated[
        list[str] | None,
        Field(
            description=(
                "If given, the request host must be in this set on the original URL and on "
                "every redirect hop, e.g. ['arxiv.org', 'export.arxiv.org']. Optional."
            ),
        ),
    ] = None,
    timeout: Annotated[
        float, Field(description="Per-request timeout in seconds. Default 30.")
    ] = DEFAULT_TIMEOUT,
    max_bytes: Annotated[
        int, Field(description="Reject downloads larger than this many bytes. Default 50 MiB.")
    ] = DEFAULT_MAX_BYTES,
    max_redirects: Annotated[
        int, Field(description="Maximum number of redirects to follow. Default 5.")
    ] = DEFAULT_MAX_REDIRECTS,
) -> ToolResult:
    try:
        hosts = frozenset(allowed_hosts) if allowed_hosts else None
        research_pdf = ResearchPDF.download(
            url,
            filepath,
            allowed_hosts=hosts,
            timeout=timeout,
            max_bytes=max_bytes,
            max_redirects=max_redirects,
        )
        return tool_result_single({"status": "ok", "path": str(research_pdf.path)})
    except PDFDownloadError as exc:
        raise ToolError(str(exc)) from exc
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc


# ------------------------------------------------------------------------------------------------ #
#                                   PDF LIST SECTIONS TOOL                                         #
# ------------------------------------------------------------------------------------------------ #
@mcp.tool(
    name="pdf_list_sections",
    description=(
        "Lists the section headings detected in a previously downloaded local PDF. "
        "Reads 'filepath' (a PDF saved by pdf_download) and returns its section headings "
        "in document order. "
        "Returns {'path': '<filepath>', 'sections': ['<heading>', ...]}. "
        "Heading detection is heuristic, so the list may include the title or a stray "
        "line; pass a heading verbatim to pdf_get_section to read its text. "
        "Use this tool to see what sections a paper has before extracting one."
    ),
)
def pdf_list_sections(
    filepath: Annotated[
        str, Field(description="Local path to a PDF previously saved by pdf_download.")
    ],
) -> ToolResult:
    try:
        with ResearchPDF(path=filepath) as research_pdf:
            return tool_result_single({"path": filepath, "sections": research_pdf.list_sections()})
    except FileNotFoundError as exc:
        raise ToolError(str(exc)) from exc
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc


# ------------------------------------------------------------------------------------------------ #
#                                    PDF GET SECTION TOOL                                          #
# ------------------------------------------------------------------------------------------------ #
@mcp.tool(
    name="pdf_get_section",
    description=(
        "Returns the body text of one named section of a local PDF. "
        "Reads 'filepath' and returns the text of the section whose heading matches "
        "'section' (case-insensitive, ignoring surrounding whitespace, leading numbering, "
        "and trailing punctuation). 'section' should be a heading returned by "
        "pdf_list_sections. "
        "Returns {'path': '<filepath>', 'heading': '<section>', 'body': '<text>'}. "
        "If no section matches, the error lists the available headings so you can retry "
        "with a valid one. "
        "Use this tool to read a specific section (for example the abstract or results) "
        "without loading the whole document."
    ),
)
def pdf_get_section(
    filepath: Annotated[
        str, Field(description="Local path to a PDF previously saved by pdf_download.")
    ],
    section: Annotated[str, Field(description="A section heading returned by pdf_list_sections.")],
) -> ToolResult:
    try:
        with ResearchPDF(path=filepath) as research_pdf:
            body = research_pdf.get_section(section)
            return tool_result_single({"path": filepath, "heading": section, "body": body})
    except (SectionNotFoundError, FileNotFoundError) as exc:
        raise ToolError(str(exc)) from exc
    except Exception as exc:
        raise ToolError(f"Internal error: {exc}") from exc
