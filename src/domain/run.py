#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Description: The Science of Venture Development                                                  #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/types                                                                       #
# Filename   : run.py                                                                              #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
"""Run entity models for Sciven pipeline executions.

A Run is a bounded execution of a single pipeline stage. Runs are first-class
operational state, not memory artifacts: they have lifecycle (created,
started, ended) and mutate over their lifetime as the stage progresses.
State transitions emit lifecycle events into the events stream; this module
does not import from the events layer.

Hierarchy:

        Entity
            Run
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid7

from sciven.domain import (
    Entity,
    EntityName,
    EntityType,
    EnumClass,
    Stage,
)


# ================================================================================================ #
#                                       ENUMERATIONS                                               #
# ================================================================================================ #
class RunStatus(EnumClass):
    """Lifecycle states for a Run.

    Attributes:
        CREATED: Run has been instantiated but work has not begun.
        RUNNING: Work is in progress.
        COMPLETED: Run terminated successfully.
        FAILED: Run terminated due to error.
        KILLED: Run terminated by gate decision (kill outcome).

    Examples:
        >>> status = RunStatus.CREATED
        >>> status.value
        'created'
    """

    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    KILLED = "killed"


# ================================================================================================ #
#                                            RUN                                                   #
# ================================================================================================ #
@dataclass(kw_only=True)
class Run(Entity):
    """Bounded execution of a single pipeline stage.

    Run is a lifecycle entity_type, not an event. It mutates as the stage
    progresses: status moves from CREATED to RUNNING to a terminal state
    (COMPLETED, FAILED, or KILLED), with timestamps recorded at each
    transition. Mutation is the responsibility of the run service; this
    dataclass is a passive record.

    This class is concrete and can be instantiated directly.

    Attributes:
        name: Short identifier for the run.
        stage: Pipeline stage this run belongs to.
        entity_type: Entity discriminator for run records.
        status: Current lifecycle state.
        created: Timestamp when the run was created.
        started: Timestamp when work began (transition to RUNNING). None
            while in CREATED state.
        ended: Timestamp when the run terminated. None until a terminal
            state is reached. Set for COMPLETED, FAILED, and KILLED alike;
            ``status`` distinguishes which terminal state was reached.
        id: Stable identifier for the run.

    Examples:
        >>> run = Run(
        ...     name='discover-pass',
        ...     stage=Stage.DISCOVERY,
        ...     agent_name='system',
        ... )
        >>> run.status
        <RunStatus.CREATED: 'created'>
    """

    name: str
    stage: Stage
    agent_name: str  # This would be the team lead agent responsible for the run.
    entity_type: EntityType = EntityType.RUN
    entity_name: EntityName = EntityName.RUN
    status: RunStatus = RunStatus.CREATED
    created: datetime = field(default_factory=lambda: datetime.now())
    started: datetime | None = None
    ended: datetime | None = None
    id: str = field(default_factory=lambda: str(uuid7()))

    def __post_init__(self):
        """Post-initialization processing to ensure consistent state."""
        if self.status == RunStatus.RUNNING and self.started is None:
            self.started = datetime.now()
        if (
            self.status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.KILLED}
            and self.ended is None
        ):
            self.ended = datetime.now()

    @property
    def embedding_text(self) -> str:
        """Returns the stage-qualified run name used for embedding.

        Returns:
            Stage value and run name joined for semantic indexing.
        """
        return f"{self.stage.value}_{self.name}"

    def start(self) -> None:
        """Transitions the run to RUNNING state and sets the started timestamp."""
        self.status = RunStatus.RUNNING
        self.started = datetime.now()

    def end(self, status: RunStatus = RunStatus.COMPLETED) -> None:
        """Transitions the run to a terminal state and sets the ended timestamp.

        Args:
            status: The terminal status to transition to. Must be one of
                COMPLETED, FAILED, or KILLED. Defaults to COMPLETED.

        Raises:
            ValueError: If ``status`` is not a terminal state.
        """
        if status not in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.KILLED}:
            raise ValueError("Invalid terminal status. Must be COMPLETED, FAILED, or KILLED.")
        self.status = status
        self.ended = datetime.now()

    @classmethod
    def create(cls, data: dict) -> Run:
        """Creates a Run instance from a serialized dictionary.

        Args:
            data: Dictionary containing serialized run fields.

        Returns:
            Hydrated Run instance.

        Raises:
            KeyError: If a required key is missing from ``data``.
            ValueError: If ``status`` is present but not a valid ``RunStatus`` value.
        """
        return cls(
            id=data["id"],
            name=data["name"],
            stage=Stage.from_value(data["stage"]),
            entity_type=EntityType.from_value(data["entity_type"]),
            entity_name=EntityName.from_value(data["entity_name"]),
            status=RunStatus.from_value(data["status"]) if "status" in data else RunStatus.CREATED,
            started=datetime.fromisoformat(data["started"]) if data.get("started") else None,
            ended=datetime.fromisoformat(data["ended"]) if data.get("ended") else None,
            created=datetime.fromisoformat(data["created"]),
            agent_name=data["agent_name"],
        )
