#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/repos                                                                       #
# Filename   : __init__.py                                                                         #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Monday April 13th 2026 03:31:35 pm                                                  #
# Modified   : Sunday May 31st 2026 12:12:58 pm                                                    #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
"""Sciven repos module."""

from dataclasses import dataclass, field

SEARCH_LIMIT_QUERY = 20
SEARCH_LIMIT_FILTER = 100000


# ------------------------------------------------------------------------------------------------ #
def get_search_limit(
    limit: int | None = None, query: str | None = None, filter: dict | None = None
) -> int:
    """Determines the appropriate search limit based on the presence of a query or filter.

    Args:
        limit: The maximum number of results to return, if specified.
        query: The search query string, if any.
        filter: The search filter dictionary, if any.

    Returns:
        The appropriate search limit for the given query and filter.
    """
    if limit is not None:
        return limit
    if query and filter:
        return SEARCH_LIMIT_QUERY
    elif filter:
        return SEARCH_LIMIT_FILTER
    else:
        return SEARCH_LIMIT_QUERY


# ------------------------------------------------------------------------------------------------ #


@dataclass
class BatchResult:
    """Summary of a batch write operation.

    Attributes:
        nsuccesses: Number of records successfully created.
        failed: List of items that failed due to existing keys.

    Examples:
        >>> result = BatchResult()
        >>> result.nsuccesses
        0
        >>> result.failed
        []
    """

    nsuccesses: int = 0
    failed: list = field(default_factory=list)
