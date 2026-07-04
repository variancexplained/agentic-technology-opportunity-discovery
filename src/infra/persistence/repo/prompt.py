#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Description: Sciven: The Science of Venture Development                                          #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/infra/persistence/repo                                                      #
# Filename   : prompt.py                                                                           #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Monday June 29th 2026 09:59:58 am                                                   #
# Modified   : Monday June 29th 2026 01:10:03 pm                                                   #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #

import logging
import warnings
from typing import TypeVar

import pandas as pd

from sciven.domain import Entity
from sciven.harness.prompt import Prompt
from sciven.infra.persistence.provider.langfuse import LangfuseAdapter
from sciven.infra.persistence.repo.base import Repo

# ================================================================================================ #
logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore", message="Core Pydantic V1")

T = TypeVar("T", bound=Entity)


# ================================================================================================ #
class PromptRepo(Repo):
    """Repository for storing and retrieving Prompt entities via Langfuse.

    Args:
        adapter (LangfuseAdapter): Persistence adapter used for prompt operations.

    Examples:
        adapter = LangfuseAdapter(...)
        repo = PromptRepo(adapter=adapter)
    """

    def __init__(self, adapter: LangfuseAdapter) -> None:
        self._adapter = adapter

    # -------------------------------------------------------------------------------------------- #
    def add(self, item: Prompt) -> None:
        """Adds a new item to the repository.

        Args:
            item: The Prompt instance to add.
        """
        self._adapter.create(name=item.name, content=item.content, labels=item.labels)

    # -------------------------------------------------------------------------------------------- #
    def exists(  # type: ignore
        self,
        name: str,
        version: int | None = None,
        label: str | None = None,
        cache_ttl_seconds: int | None = None,
    ) -> bool:
        """Check whether a prompt exists for the given selector.

        Args:
            name: The name of the prompt.
            version: Optional version of the prompt.
            label: Optional label for the prompt.
            cache_ttl_seconds: Optional cache TTL in seconds.

        Returns:
            bool: True if a matching prompt exists, otherwise False.
        """
        return bool(
            self._adapter.exists(
                name=name, version=version, label=label, cache_ttl_seconds=cache_ttl_seconds
            )
        )

    # -------------------------------------------------------------------------------------------- #
    def get(  # type: ignore
        self,
        name: str,
        version: int | None = None,
        label: str | None = None,
        variables: dict | None = None,
        cache_ttl_seconds: int | None = None,
    ) -> Prompt:
        """Retrieves a single item by name, version, and label.

        Args:
            name: The name of the prompt.
            version: Optional version of the prompt.
            label: Optional label for the prompt.
            variables: Optional template variables used when compiling content.
            cache_ttl_seconds: Optional cache TTL in seconds.

        Returns:
            Prompt: The deserialized prompt model.
        """
        prompt = self._adapter.read(
            name=name, version=version, label=label, cache_ttl_seconds=cache_ttl_seconds
        )
        content = prompt.compile(**variables) if variables else prompt.compile()
        return Prompt(
            name=prompt.name,
            version=prompt.version,
            variables=prompt.variables or {},
            labels=prompt.labels,
            content=content,
            prompt=prompt,
        )

    # -------------------------------------------------------------------------------------------- #
    def remove(self, item: Prompt) -> None:
        """Remove a prompt from the repository.

        Args:
            item: Entity domain model to remove.
            cache_ttl_seconds: Optional cache TTL in seconds.
        """
        if item.labels:
            for label in item.labels:
                self._adapter.delete(name=item.name, version=item.version, label=label)
        else:
            self._adapter.delete(name=item.name, version=item.version)

    # -------------------------------------------------------------------------------------------- #
    def deserialize(self, data: dict) -> Prompt:
        """Deserializes a value dictionary into the target domain model.

        Args:
            data: Value dictionary retrieved from the store.

        Returns:
            Deserialized domain model instance.

        Raises:
            NotImplementedError: Deserialization is not implemented for PromptRepo.
        """
        raise NotImplementedError("Deserialization is not implemented for PromptRepo.")

    # -------------------------------------------------------------------------------------------- #
    def deserialize_batch(self, items: list[dict]) -> list[Prompt]:
        """Deserializes a list of value dictionaries into domain models.

        Args:
            items: List of value dictionaries to deserialize.

        Returns:
            List of successfully deserialized domain models.

        Raises:
            NotImplementedError: Batch deserialization is not implemented for PromptRepo.
        """
        raise NotImplementedError("Batch deserialization is not implemented for PromptRepo.")

    # -------------------------------------------------------------------------------------------- #
    def summary(self, *args, **kwargs) -> pd.DataFrame:
        """Generates a summary of items in the repository.

        This method can be overridden by subclasses to provide custom
        summaries based on the specific domain model.

        Args:
            *args: Positional arguments for summary generation.
            **kwargs: Keyword arguments for summary generation.

        Returns:
            A DataFrame containing summary statistics or insights.
        """
        prompt_list = self._adapter.list_prompts()
        df = pd.DataFrame([p.model_dump() for p in prompt_list])
        return df
