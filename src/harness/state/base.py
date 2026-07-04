#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Description: Sciven: The Science of Venture Development                                          #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/application                                                                 #
# Filename   : core.py                                                                             #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Sunday June 14th 2026 09:04:14 am                                                   #
# Modified   : Saturday June 27th 2026 03:07:31 am                                                 #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
"""Core module for the application package."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid7

from sciven.domain.core import DataClass, Stage, TaskType


# ------------------------------------------------------------------------------------------------ #
#                                         STATE BASE CLASS                                         #
# ------------------------------------------------------------------------------------------------ #
@dataclass(kw_only=True)
class State(DataClass, ABC):
    """Base dataclass for persisted application state.

    Attributes:
        id: Stable state identifier derived from the key.
        run_id: Identifier of the run this state belongs to.
        stage: Pipeline stage associated with the state.
        task_type: Task category associated with the state.
        agent_name: Agent responsible for the state record.

    Examples:
        >>> state = DocumentCuratorState(
        ...     run_id="run-1",
        ...     stage=Stage.DISCOVERY,
        ...     task_type=TaskType.CURATE_DOCUMENTS,
        ...     agent_name="discover-agent",
        ... )
    """

    id: str = field(default_factory=lambda: str(uuid7()))
    run_id: str
    stage: Stage
    task_type: TaskType
    agent_name: str

    def __post_init__(self):
        """Post-initialization processing to set the unique identifier."""
        self.id = self.key

    # -------------------------------------------------------------------------------------------- #
    @property
    def namespace(self) -> tuple[str, ...]:
        """Namespace for this object, used for storage and retrieval."""
        return (self.stage.value, self.task_type.value)

    # -------------------------------------------------------------------------------------------- #
    @property
    def key(self) -> str:
        """Unique key for this object."""
        return f"{self.stage.value} | {self.task_type.value} | {self.run_id} | {self.agent_name}"

    # -------------------------------------------------------------------------------------------- #
    @property
    def value(self) -> dict[str, Any]:
        """Returns the serialized state payload.

        Returns:
            Dictionary representation of this state instance.
        """
        return self.as_dict()

    # -------------------------------------------------------------------------------------------- #
    @property
    def index(self) -> list[str] | None:
        """List of value fields to use for indexing and search.

        This property can be overridden by subclasses to specify which fields
        of the stored value should be indexed for search. By default, it returns
        ``None``, indicating that no specific index fields are defined.

        Returns:
            A list of field names to index, or ``None`` if no specific index is defined.
        """
        return None

    # -------------------------------------------------------------------------------------------- #
    @classmethod
    @abstractmethod
    def create(cls, *args, **kwargs) -> State:
        """Factory method to create a new state instance."""
        pass


# ------------------------------------------------------------------------------------------------ #
#                                      OPERATOR BASE CLASS                                         #
# ------------------------------------------------------------------------------------------------ #
class Operator(ABC):
    """Base class for application operators.

    Args:
        run_id: Unique identifier for the operator run.
        stage: Pipeline stage for this operator.
        task_type: Task type for this operator.
        agent_name: Name of the agent operating this operator.

    Examples:
        >>> class ExampleOperator(Operator):
        ...     def __init__(self, run_id: str, stage: Stage, task_type: TaskType, agent_name: str) -> None:
        ...         super().__init__(run_id, stage, task_type, agent_name)
        >>> op = ExampleOperator("run-1", Stage.DISCOVERY, TaskType.CURATE_DOCUMENTS, "agent")
    """

    @abstractmethod
    def __init__(self, run_id: str, stage: Stage, task_type: TaskType, agent_name: str) -> None:
        self._run_id = run_id
        self._stage = stage
        self._task_type = task_type
        self._agent_name = agent_name

    # -------------------------------------------------------------------------------------------- #
    @property
    def namespace(self) -> tuple[str, ...]:
        """Namespace for this object, used for storage and retrieval."""
        return (self._stage.value, self._task_type.value)

    # -------------------------------------------------------------------------------------------- #
    @property
    def key(self) -> str:
        """Unique key for this object."""
        return (
            f"{self._stage.value} | {self._task_type.value} | {self._run_id} | {self._agent_name}"
        )
