#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/repos                                                                       #
# Filename   : run.py                                                                              #
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
"""Run repository for the Sciven research pipeline."""

import logging

from sciven.domain import EntityType, Stage
from sciven.domain.run import Run, RunStatus
from sciven.infra.persistence.repo.base import Repo

# ------------------------------------------------------------------------------------------------ #
logger = logging.getLogger(__name__)
# ------------------------------------------------------------------------------------------------ #
#                                 SOURCE REPOSITORY                                                #
# ------------------------------------------------------------------------------------------------ #


class RunRepo(Repo):
    """Repository for persisting and retrieving Run domain objects.

    Args:
        adapter: Store adapter used for persistence and search operations.

    Examples:
        >>> from sciven.adapters.langgraph.store import StoreAdapter
        >>> adapter = StoreAdapter()
        >>> repo = RunRepo(adapter=adapter)
    """

    # -------------------------------------------------------------------------------------------- #
    def deserialize(self, data: dict) -> Run:
        """Deserializes a value dictionary to a Run instance.

        Args:
            data: Value dictionary containing a ``stage`` field used to
                dispatch to the correct run class.

        Returns:
            A Run instance.
        """
        return Run.create(data)

    # -------------------------------------------------------------------------------------------- #
    def deserialize_batch(self, items: list[dict]) -> list[Run]:
        """Deserializes a list of value dictionaries to Run instances.

        Silently skips items that fail deserialization and logs the error.

        Args:
            items: List of value dictionaries to deserialize.

        Returns:
            List of successfully deserialized Run instances.
        """
        runs: list[Run] = []
        for data in items:
            try:
                runs.append(self.deserialize(data))
            except (ValueError, KeyError) as exc:
                logger.warning("Failed to deserialize run: %s", exc)
        return runs

    # -------------------------------------------------------------------------------------------- #
    def summary(self, stage: Stage, limit: int = 1_000_000) -> dict:
        """Summarizes runs for a pipeline stage.

        Args:
            stage: Pipeline stage to summarize.
            limit: Upper bound on runs fetched. Defaults to 100000.

        Returns:
            Dictionary with total and counts by RunStatus.
        """
        namespace = (stage.value, EntityType.RUN.value)
        runs = self.search(namespace, limit=limit)

        status_counts = {s.value: 0 for s in RunStatus}
        for run in runs:
            status_counts[run.status.value] += 1

        return {
            "total": len(runs),
            "status_counts": status_counts,
        }
