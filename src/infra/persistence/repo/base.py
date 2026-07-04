#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Description: Sciven: The Science of Venture Development                                          #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/infra/persistence/repo                                                      #
# Filename   : base.py                                                                             #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Wednesday May 27th 2026 05:15:27 pm                                                 #
# Modified   : Monday June 29th 2026 11:52:37 am                                                   #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
"""Base repository abstractions for Sciven persistence layers."""

import logging
import warnings
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

import pandas as pd

from sciven.domain import Entity
from sciven.infra.persistence.provider.langgraph.store import StoreAdapter, StoreItem
from sciven.infra.persistence.repo import BatchResult, get_search_limit

# ================================================================================================ #
logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore", message="Core Pydantic V1")

T = TypeVar("T", bound=Entity)


# ================================================================================================ #
class Repo(Generic[T], ABC):  # noqa: UP046
    """Abstract base class for repos in Sciven.

    Defines the shared repository interface for persisting and retrieving
    domain models backed by a ``StoreAdapter``.

    Args:
        adapter: Store adapter used for persistence and search operations.

    Examples:
        Instantiate a concrete subclass with a configured adapter:

        >>> adapter = StoreAdapter(...)
        >>> repo = ConcreteRepo(adapter=adapter)
    """

    def __init__(self, adapter: StoreAdapter) -> None:
        self._adapter = adapter

    # -------------------------------------------------------------------------------------------- #
    def count(self, namespace: tuple[str, ...]) -> int:
        """Counts the number of items in a given namespace.

        Args:
            namespace: The namespace tuple to count items within.

        Returns:
            The total number of items in the namespace.
        """
        return self._adapter.count(namespace)

    # -------------------------------------------------------------------------------------------- #
    def add(self, item: T) -> None:
        """Adds a new item to the repository.

        Args:
            item: Entity domain model to store.

        Raises:
            ValueError: If an item with the same key already exists
                in the namespace.
        """
        if self.exists(item=item):
            msg = f"{item.__class__.__name__} with key '{item.key}' already exists in namespace '{item.namespace}'."
            raise ValueError(msg)
        store_item = self._get_store_item(item)
        self._adapter.create(store_item)

    # -------------------------------------------------------------------------------------------- #
    def add_batch(self, items: list[T]) -> BatchResult:
        """Adds multiple items, skipping duplicates.

        Args:
            items: Entity domain models to store.

        Returns:
            A BatchResult summarizing successes and failures.
        """
        result = BatchResult()
        for item in items:
            try:
                self.add(item)
                result.nsuccesses += 1
            except ValueError as error:
                logger.warning(error)
                result.failed.append(item)
        return result

    # -------------------------------------------------------------------------------------------- #
    def upsert(self, item: T) -> None:
        """Write an item to the repository, replacing an existing record.

        This implementation removes the current item (if present) and adds the
        provided item.

        Args:
            item: Entity domain model to store or overwrite.
        """
        self.remove(item=item)
        self.add(item=item)

    # -------------------------------------------------------------------------------------------- #
    def exists(self, item: T, **kwargs) -> bool:
        """Checks whether an item with the same key already exists.

        Args:
            item: Entity domain model to check.
            **kwargs: Additional repository-specific options. Unused in the
                base implementation.

        Returns:
            ``True`` if an item with the same namespace and key exists,
            otherwise ``False``.
        """
        return bool(self._adapter.exists(item.namespace, item.key))

    # -------------------------------------------------------------------------------------------- #
    def get(
        self, namespace: tuple[str, ...] | None = None, key: str | None = None, **kwargs
    ) -> T | None:
        """Retrieves a single item by namespace and key.

        Args:
            namespace: The namespace tuple identifying the partition.
            key: The unique key within the namespace.
            **kwargs: Additional repository-specific options. Unused in the
                base implementation.

        Returns:
            The deserialized domain model, or ``None`` if not found.
        """
        data = self._adapter.read(namespace, key)
        if data is None:
            return None
        return self.deserialize(data)

    # -------------------------------------------------------------------------------------------- #
    def search(
        self,
        namespace: tuple[str, ...],
        query: str | None = None,
        filter: dict | None = None,
        limit: int | None = None,
    ) -> list[T]:
        """Searches for items within a namespace.

        Args:
            namespace: The namespace prefix to search within.
            query: Optional semantic search text.
            filter: Optional structured filter on stored values.
            limit: Maximum number of results to return.

        Returns:
            List of deserialized domain models ranked by relevance.
        """
        limit = get_search_limit(limit=limit, query=query, filter=filter)
        items = self._adapter.search(namespace, filter=filter, query=query, limit=limit)
        return self.deserialize_batch(items)

    # -------------------------------------------------------------------------------------------- #
    def remove(self, item: T) -> None:
        """Removes an item from the repository.

        Args:
            item: Entity domain model to remove.
        """
        self._adapter.delete(item.namespace, item.key)

    # -------------------------------------------------------------------------------------------- #
    def _get_store_item(self, item: T) -> StoreItem:
        """Convert a domain model to a StoreItem for persistence."""
        return StoreItem(
            namespace=item.namespace,
            key=item.key,
            value=item.value,
            index=item.index,
        )

    # -------------------------------------------------------------------------------------------- #
    def reset(self, namespace: tuple[str, ...]) -> None:
        """Deletes all items within a given namespace.

        Args:
            namespace: The namespace tuple to clear.
        """
        self._adapter.reset(namespace)

    # -------------------------------------------------------------------------------------------- #
    @abstractmethod
    def deserialize(self, data: dict) -> T:
        """Deserializes a value dictionary into the target domain model.

        Args:
            data: Value dictionary retrieved from the store.

        Returns:
            Deserialized domain model instance.

        Raises:
            ValueError: If the data cannot be mapped to a valid domain model.
        """
        pass

    # -------------------------------------------------------------------------------------------- #
    @abstractmethod
    def deserialize_batch(self, items: list[dict]) -> list[T]:
        """Deserializes a list of value dictionaries into domain models.

        Args:
            items: List of value dictionaries to deserialize.

        Returns:
            List of successfully deserialized domain models.
        """

    # -------------------------------------------------------------------------------------------- #
    @abstractmethod
    def summary(self, *args, **kwargs) -> dict[str, Any] | pd.DataFrame:
        """Generates a summary of items in the repository.

        This method can be overridden by subclasses to provide custom
        summaries based on the specific domain model.

        Args:
            *args: Positional arguments for summary generation.
            **kwargs: Keyword arguments for summary generation.

        Returns:
            A dictionary containing summary statistics or insights.
        """
