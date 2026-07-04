#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Description: The Science of Venture Development                                                  #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/types/search                                                                #
# Filename   : source.py                                                                           #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Wednesday April 29th 2026 05:15:52 am                                               #
# Modified   : Saturday June 13th 2026 10:22:43 am                                                 #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
"""Source descriptor for web search targets."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field
from pydantic.dataclasses import dataclass

from sciven.domain import Entity, EntityType, EnumClass, Stage
from sciven.domain.core import EntityName
from sciven.utils.formatting import normalize_url


# ------------------------------------------------------------------------------------------------ #
class SourceType(EnumClass):
    """Enumerates supported source categories for discovery targets.

    Attributes:
        PAPER: Academic papers and preprints.
        PUBLICATION: Journals, magazines, and periodicals.
        WEBSITE: General websites and landing pages.
        BLOG: Blog posts and editorial articles.
        NEWS: News media articles.
        SOCIAL_MEDIA: Social media posts and threads.

    Examples:
        >>> source_type = SourceType.PAPER
        >>> source_type.value
        'paper'
        >>> SourceType.from_value('website')
        <SourceType.WEBSITE: 'website'>
    """

    PAPER = "paper"
    PUBLICATION = "publication"
    WEBSITE = "website"
    BLOG = "blog"
    NEWS = "news"
    SOCIAL_MEDIA = "social_media"


# ------------------------------------------------------------------------------------------------ #
@dataclass(kw_only=True)
class Source(Entity):
    """Represents a normalized source record used across pipeline stages.

    Attributes:
        name: Human-readable source name.
        description: Short description of the source.
        url: Canonical source URL.
        source_type: Category describing the source medium.
        tier: Priority tier from 1 (highest) to 3 (lowest).

    Examples:
        >>> source = Source(
        ...     name="arXiv",
        ...     description="Open-access research paper repository",
        ...     url="https://arxiv.org",
        ...     source_type=SourceType.PAPER,
        ...     tier=1,
        ...     agent_name="system",
        ... )
        >>> source.entity_name.value
        'source'
    """

    name: str
    description: str
    url: str
    source_type: SourceType
    tier: Annotated[int, Field(ge=1, le=3)]

    stage: Stage = Stage.DISCOVERY
    entity_type: EntityType = EntityType.SOURCE
    entity_name: EntityName = EntityName.SOURCE

    def __post_init__(self) -> None:
        """Normalizes the source URL after dataclass initialization.

        Called automatically after the dataclass is constructed. Ensures all URLs
        are in a consistent normalized format.
        """
        if self.url:
            self.url = normalize_url(self.url)

    @property
    def embedding_text(self) -> str:
        """Returns the text used to generate the source embedding vector.

        Returns:
            Source name and description joined for semantic indexing.
        """
        return f"{self.name} {self.description}"

    @classmethod
    def create(cls, data: dict) -> Source:
        """Create a source instance from a serialized value dictionary.

        Args:
            data: Mapping containing serialized source fields.

        Returns:
            A Source instance created from the provided data.

        Raises:
            KeyError: If required keys are missing from data.
            ValueError: If enum values are invalid.
        """
        return cls(
            name=data["name"],
            description=data["description"],
            url=data["url"],
            source_type=SourceType.from_value(data["source_type"]),
            tier=data["tier"],
            id=data.get("id"),
            stage=Stage.from_value(data["stage"]),
            entity_type=EntityType.from_value(data["entity_type"]),
            entity_name=EntityName.from_value(data["entity_name"]),
            agent_name=data.get("agent_name"),
            created=datetime.fromisoformat(data["created"]),
            modified=datetime.fromisoformat(data["modified"]) if data.get("modified") else None,
        )
