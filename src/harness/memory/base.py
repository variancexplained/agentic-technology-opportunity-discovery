#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Description: Sciven: The Science of Venture Development                                          #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/platform/memory                                                             #
# Filename   : base.py                                                                             #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Friday June 26th 2026 09:19:24 pm                                                   #
# Modified   : Saturday June 27th 2026 05:11:26 am                                                 #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid7

from sciven.domain.core import DataClass, Stage, TaskType


# ------------------------------------------------------------------------------------------------ #
#                                      MEMORY BASE CLASS                                           #
# ------------------------------------------------------------------------------------------------ #
@dataclass(kw_only=True)
class Memory(DataClass, ABC):
    """Base dataclass for persisted memory state.

    Attributes:
        id: Stable state identifier derived from the key.
        run_id: Identifier of the run this state belongs to.
        stage: Pipeline stage associated with the state.
        task_type: Task category associated with the state.
        agent_name: Agent responsible for the state record.
    """

    id: str = field(default_factory=lambda: str(uuid7()))
    run_id: str
    stage: Stage
    task_type: TaskType
    agent_name: str
    accessed: datetime = field(default_factory=datetime.now)
    created: datetime = field(default_factory=datetime.now)

    # -------------------------------------------------------------------------------------------- #
    @property
    def namespace(self) -> tuple[str, ...]:
        """Namespace for this object, used for storage and retrieval."""
        return (self.stage.value, self.task_type.value)

    # -------------------------------------------------------------------------------------------- #
    @property
    def key(self) -> str:
        """Unique key for this object."""
        return self.id

    # -------------------------------------------------------------------------------------------- #
    @property
    def value(self) -> dict[str, Any]:
        """Returns the serialized state payload.

        Returns:
            Dictionary representation of this state instance.
        """
        return self.as_dict()

    # -------------------------------------------------------------------------------------------- #
    @classmethod
    @abstractmethod
    def create(cls, data: dict) -> Memory:
        """Creates an instance of the class from a dictionary."""
