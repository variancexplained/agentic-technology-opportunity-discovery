#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Description: Sciven: The Science of Venture Development                                          #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/platform/memory                                                             #
# Filename   : reflection.py                                                                       #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Friday June 26th 2026 09:19:24 pm                                                   #
# Modified   : Saturday June 27th 2026 06:04:34 am                                                 #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sciven.domain.core import Stage, TaskType
from sciven.harness.memory.base import Memory


# ------------------------------------------------------------------------------------------------ #
#                                SEMANTIC MEMORY BASE CLASS                                        #
# ------------------------------------------------------------------------------------------------ #
@dataclass(kw_only=True)
class ReflectionMemory(Memory):
    """Represents a memory state that is semantic in nature."""

    content: str = field(default="")
    related_episodes: list[str] = field(default_factory=list)
    impact: float = field(default=0.5)

    # -------------------------------------------------------------------------------------------- #
    @property
    def value(self) -> dict[str, Any]:
        """Returns the serialized entity payload.

        Returns:
            Dictionary representation of this entity instance.
        """
        data = self.as_dict()
        data["embedding_text"] = self.embedding_text
        return data

    # -------------------------------------------------------------------------------------------- #
    @property
    def index(self) -> list[str] | None:
        """List of value fields to use for indexing and search."""
        return ["embedding_text"]

    # -------------------------------------------------------------------------------------------- #
    @property
    def embedding_text(self) -> str:
        """Text used for embedding this object in vector stores."""
        return self.content

    # -------------------------------------------------------------------------------------------- #
    @classmethod
    def create(cls, data: dict) -> ReflectionMemory:
        """Creates an instance of the class from a dictionary."""
        return cls(
            id=data.get("id"),
            run_id=data.get("run_id"),
            stage=Stage.from_value(data["stage"]),
            task_type=TaskType.from_value(data["task_type"]),
            agent_name=data.get("agent_name"),
            content=data.get("content", ""),
            related_episodes=data.get("related_episodes", []),
            impact=data.get("impact", 0.5),
            accessed=datetime.fromisoformat(data["accessed"]),
            created=datetime.fromisoformat(data["created"]),
        )
