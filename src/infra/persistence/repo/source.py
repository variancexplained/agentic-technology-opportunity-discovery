#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/repos                                                                       #
# Filename   : source.py                                                                           #
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
"""Source repository for the Sciven research pipeline."""

import logging

from sciven.domain import EntityType, Stage
from sciven.domain.source import Source
from sciven.infra.persistence.repo.base import Repo

# ------------------------------------------------------------------------------------------------ #
logger = logging.getLogger(__name__)
# ------------------------------------------------------------------------------------------------ #
#                                 SOURCE REPOSITORY                                                #
# ------------------------------------------------------------------------------------------------ #


class SourceRepo(Repo[Source]):
    """Repository for persisting and retrieving Source domain objects.

    Args:
        adapter: Store adapter used for persistence and search operations.

    Examples:
        >>> from sciven.adapters.langgraph.store import StoreAdapter
        >>> adapter = StoreAdapter()
        >>> repo = SourceRepo(adapter=adapter)
    """

    # -------------------------------------------------------------------------------------------- #
    def deserialize(self, data: dict) -> Source:
        """Deserializes a value dictionary to a Source instance.

        Args:
            data: Value dictionary containing a ``stage`` field used to
                dispatch to the correct source class.

        Returns:
            A Source instance.
        """
        return Source.create(data)

    # -------------------------------------------------------------------------------------------- #
    def deserialize_batch(self, items: list[dict]) -> list[Source]:
        """Deserializes a list of value dictionaries to Source instances.

        Silently skips items that fail deserialization and logs the error.

        Args:
            items: List of value dictionaries to deserialize.

        Returns:
            List of successfully deserialized Source instances.
        """
        sources: list[Source] = []
        for data in items:
            try:
                sources.append(self.deserialize(data))
            except (ValueError, KeyError) as exc:
                logger.warning("Failed to deserialize source: %s", exc)
        return sources

    # -------------------------------------------------------------------------------------------- #
    def summary(self, limit: int = 100_000) -> dict:
        """Summarizes sources across type and tier.

        Args:
            limit: Upper bound on sources fetched. Defaults to 100000.

        Returns:
            Dictionary with total and breakdowns by source_type and tier.
        """
        namespace = (Stage.DISCOVERY.value, EntityType.SOURCE.value)
        sources = self.search(namespace, limit=limit)

        total = len(sources)
        if total == 0:
            return {
                "total": 0,
                "by_source_type": {},
                "by_tier": {i: 0 for i in range(1, 4)},
            }

        by_source_type: dict[str, int] = {}
        by_tier: dict[int, int] = {1: 0, 2: 0, 3: 0}

        for s in sources:
            by_source_type[s.source_type.value] = by_source_type.get(s.source_type.value, 0) + 1
            by_tier[s.tier] += 1

        return {
            "total": total,
            "by_source_type": by_source_type,
            "by_tier": by_tier,
        }
