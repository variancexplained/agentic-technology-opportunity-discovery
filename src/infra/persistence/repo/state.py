#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/repos                                                                       #
# Filename   : state.py                                                                            #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Tuesday April 14th 2026                                                             #
# Modified   : Monday June 29th 2026 07:05:45 am                                                   #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
"""State repository for the Sciven research pipeline."""

import logging

import pandas as pd
from sciven.harness.state1.base import State

from sciven.application.discover.curate.memory import DocumentCuratorState
from sciven.domain import Stage
from sciven.domain.core import TaskType
from sciven.infra.persistence.repo.base import Repo

logger = logging.getLogger(__name__)
# ------------------------------------------------------------------------------------------------ #
#                                   SEARCH API MAPPING                                             #
# ------------------------------------------------------------------------------------------------ #
TASKTYPE_STATE_MAP: dict[TaskType, type[State]] = {TaskType.CURATE_DOCUMENTS: DocumentCuratorState}

# ================================================================================================ #
#                                REFLECTION REPOSITORY                                             #
# ================================================================================================ #


class StateRepo(Repo):
    """Repository for managing State records.

    Provides methods for creating, retrieving, and searching states,
    which capture agent learnings from research cycles.

    Args:
        adapter: Store adapter for underlying CRUD operations.

    Examples:
        >>> from sciven.adapters.langgraph.store import StoreAdapter
        >>> adapter = StoreAdapter()
        >>> repo = StateRepo(adapter=adapter)
    """

    # -------------------------------------------------------------------------------------------- #
    def deserialize(self, data: dict) -> State:
        """Deserializes a value dictionary to a State instance.

        Args:
            data: Value dictionary containing a ``task_type`` field used to
                dispatch to the correct state class.

        Returns:
            A State instance.
        """
        state_subclass = TASKTYPE_STATE_MAP.get(TaskType.from_value(data["task_type"]))
        if not state_subclass:  # pragma: no cover - TaskType.from_value already rejects unknowns
            raise ValueError(f"Unsupported TaskType type: {data.get('task_type')}")
        return state_subclass.create(data)

    # -------------------------------------------------------------------------------------------- #
    def deserialize_batch(self, items: list[dict]) -> list[State]:
        """Deserializes a list of value dictionaries to State instances.

        Silently skips items that fail deserialization and logs the error.

        Args:
            items: List of value dictionaries to deserialize.

        Returns:
            List of successfully deserialized State instances.
        """
        states: list[State] = []
        for data in items:
            try:
                states.append(self.deserialize(data))
            except (ValueError, KeyError) as exc:
                logger.warning("Failed to deserialize state: %s", exc)
        return states

    # -------------------------------------------------------------------------------------------- #
    def summary(self, stage: Stage, task_type: TaskType, limit: int = 1_000_000) -> pd.DataFrame:
        """Summarize task states in a stage/task namespace as tabular rows.

        Args:
            stage: Stage used to scope the summary.
            task_type: TaskType used to filter the summary.
            limit: Maximum number of states to fetch from storage.

        Returns:
            A DataFrame with one row per stored state and columns for stage,
            task metadata, document counts, and average page score.
        """
        namespace = (stage.value, task_type.value)
        states = self.search(namespace, limit=limit)

        df = pd.DataFrame(
            [
                {
                    "Stage": state.stage.value,
                    "Task Type": state.task_type.value,
                    "Run ID": state.run_id,
                    "Agent Name": state.agent_name,
                    "Query Count": state.query_count,
                    "Total Document Count": state.total_document_count,
                    "New Document Count": state.new_document_count,
                    "New Document Ratio": state.new_document_ratio,
                    "Average Score": sum(state.page_average_scores) / len(state.page_average_scores)
                    if state.page_average_scores
                    else None,
                }
                for state in states
            ]
        )
        return df
