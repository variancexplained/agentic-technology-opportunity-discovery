#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Description: Sciven: The Science of Venture Development                                          #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/harness                                                                     #
# Filename   : prompt.py                                                                           #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Monday June 29th 2026 10:23:56 am                                                   #
# Modified   : Monday June 29th 2026 11:20:47 am                                                   #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
from dataclasses import dataclass, field
from typing import Any

from sciven.domain.core import DataClass


# ------------------------------------------------------------------------------------------------ #
@dataclass(kw_only=True)
class Prompt(DataClass):
    """Represents a prompt with its associated metadata and content.

    Examples:
        prompt = Prompt(name="discover", version=1)

    Attributes:
        name (str): The name of the prompt.
        version (int | None): The version of the prompt.
        labels (list[str]): Optional list of labels for the prompt.
        content (str): The content of the prompt.
        variables (dict): Variables referenced by the prompt content.
        prompt (Any | None): Backing prompt object from an external provider.
    """

    name: str
    version: int | None = None
    labels: list[str] = field(default_factory=list)
    content: str = field(default_factory=str)
    variables: dict = field(default_factory=dict)
    prompt: Any | None = None  # Placeholder for the actual prompt object

    def __post_init__(self):
        """Post-initialization processing to ensure the prompt object is set."""
        if not self.labels:
            self.labels = ["production"]
