#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/repos                                                                       #
# Filename   : reflection.py                                                                       #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Tuesday April 14th 2026                                                             #
# Modified   : Monday June 29th 2026 06:49:26 am                                                   #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
"""Reflection repository for the Sciven research pipeline."""

import logging
from operator import attrgetter
from typing import Any

from sciven.domain.reflection import Reflection

from sciven.domain import Stage
from sciven.infra.persistence.repo.base import Repo

logger = logging.getLogger(__name__)
# ================================================================================================ #
#                                REFLECTION REPOSITORY                                             #
# ================================================================================================ #


class ReflectionRepo(Repo):
    """Repository for managing Reflection records.

    Provides methods for creating, retrieving, and searching reflections,
    which capture agent learnings from research cycles.

    Args:
        adapter: Store adapter for underlying CRUD operations.

    Examples:
        >>> from sciven.adapters.langgraph.store import StoreAdapter
        >>> adapter = StoreAdapter()
        >>> repo = ReflectionRepo(adapter=adapter)
    """

    # -------------------------------------------------------------------------------------------- #
    def search(
        self,
        namespace: tuple[str, ...],
        query: str | None = None,
        filter: dict | None = None,
        limit: int | None = None,
        sort_by: str = "relevance",  # relevance or recency
        sort_reverse: bool = True,
    ) -> list[Reflection]:
        """Search reflections within a namespace.

        Args:
            namespace: Namespace tuple used to scope the search.
            query: Optional text query.
            filter: Optional filter dictionary passed to the adapter.
            limit: Maximum number of items to fetch.
            sort_by: Reflection field used to sort results.
            sort_reverse: Whether to sort in descending order.

        Returns:
            Reflections matching the search criteria.
        """
        items = self._adapter.search(namespace, filter=filter, query=query, limit=limit)
        reflections = self.deserialize_batch(items)
        if sort_by == "relevance":
            return reflections  # Assume adapter returns relevance-sorted results

        return sorted(reflections, key=attrgetter(sort_by), reverse=sort_reverse)

    # -------------------------------------------------------------------------------------------- #
    def deserialize(self, data: dict) -> Reflection:
        """Deserializes a value dictionary to a Reflection instance.

        Args:
            data: Value dictionary containing a ``stage`` field used to
                dispatch to the correct reflection class.

        Returns:
            A Reflection instance.
        """
        return Reflection.create(data)

    # -------------------------------------------------------------------------------------------- #
    def deserialize_batch(self, items: list[dict]) -> list[Reflection]:
        """Deserializes a list of value dictionaries to Reflection instances.

        Silently skips items that fail deserialization and logs the error.

        Args:
            items: List of value dictionaries to deserialize.

        Returns:
            List of successfully deserialized Reflection instances.
        """
        reflections: list[Reflection] = []
        for data in items:
            try:
                reflections.append(self.deserialize(data))
            except (ValueError, KeyError) as exc:
                logger.warning("Failed to deserialize reflection: %s", exc)
        return reflections

    # -------------------------------------------------------------------------------------------- #
    def summary(self, stage: Stage, limit: int = 1_000_000) -> dict[str, Any]:
        """Summarize reflections by agent_name within a stage namespace.

        Args:
            stage: Stage used to scope the summary.
            limit: Maximum number of reflections to fetch from storage.

        Returns:
            A dictionary containing the total count and per-agent_name counts.
        """
        namespace = (stage.value,)
        reflections = self.search(namespace, limit=limit)

        total = len(reflections)
        if total == 0:
            return {"total": 0, "by_agent_name": {}}

        agent_name_counts: dict[str, int] = {}
        for r in reflections:
            agent_name = r.agent_name or "unknown"
            agent_name_counts[agent_name] = agent_name_counts.get(agent_name, 0) + 1

        return {"total": total, "by_agent_name": agent_name_counts}
