#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Description: Sciven: The Science of Venture Development                                          #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/platform/memory                                                             #
# Filename   : episodic.py                                                                         #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Friday June 26th 2026 09:19:24 pm                                                   #
# Modified   : Saturday June 27th 2026 06:11:59 am                                                 #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
from dataclasses import dataclass, field
from typing import Any

from sciven.harness.memory.base import Memory


# ------------------------------------------------------------------------------------------------ #
#                                  EPISODIC MEMORY BASE CLASS                                      #
# ------------------------------------------------------------------------------------------------ #
@dataclass(kw_only=True)
class EpisodicMemory(Memory):
    """Represents a memory state that is episodic in nature."""

    context: str
    action_taken: str
    outcome: str = field(default="")

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
        return self.context + " " + self.action_taken + " " + self.outcome
