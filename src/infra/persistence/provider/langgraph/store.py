#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/adapters                                                                    #
# Filename   : store.py                                                                            #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Tuesday April 8th 2026                                                              #
# Modified   : Monday June 29th 2026 08:07:18 am                                                   #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
"""Store models and adapter helpers for LangGraph Postgres stores."""

from dataclasses import dataclass

import psycopg
from langgraph.store.postgres import PostgresStore

from sciven.domain import DataClass
from sciven.infra.persistence.provider.base import PersistenceAdapter
from sciven.infra.persistence.provider.langgraph.embedding import EmbeddingConfig

# ------------------------------------------------------------------------------------------------ #
DUPLICATE_THRESHOLD = 0.95


# ================================================================================================ #
#                                      EXCEPTIONS                                                  #
# ================================================================================================ #
class StoreNotConnectedError(RuntimeError):
    """Raised when a StoreAdapter method is called before connect()."""


# ================================================================================================ #
#                                      STORE ITEM                                                  #
# ================================================================================================ #
@dataclass
class StoreItem(DataClass):
    """Represents the payload required to write a record to the store.

    Args:
        namespace: Namespace tuple that partitions records in the store.
        key: Unique key for the stored record.
        value: Dictionary payload to persist.
        index: Optional text to embed and index for semantic search.
    """

    namespace: tuple[str, ...]
    key: str
    value: dict
    index: str | None


# ================================================================================================ #
#                                    STORE ADAPTER                                                 #
# ================================================================================================ #
class StoreAdapter(PersistenceAdapter):
    """Adapter for CRUD and semantic search over stored records.

    Manages connection lifecycle and wraps a ``PostgresStore`` to provide
    convenience methods for synchronous create, read,
    search, delete, and existence checks.

    LangGraph store types (``Item``, ``SearchItem``) are consumed internally
    and never exposed to callers. All read and search methods return plain
    dictionaries.

    Args:
        db_uri: PostgreSQL connection URI used to open a psycopg connection.
        embedding_config: Optional embedding configuration used to enable
            semantic indexing in the underlying store.
    """

    def __init__(
        self,
        db_uri: str,
        embedding_config: EmbeddingConfig | None = None,
    ) -> None:
        self._db_uri = db_uri
        self._embedding_config = embedding_config
        self._connection: psycopg.Connection | None = None
        self._store: PostgresStore | None = None

    # -------------------------------------------------------------------------------------------- #
    #                                       CONNECTION                                             #
    # -------------------------------------------------------------------------------------------- #
    def connect(self) -> None:
        """Opens the database connection and initializes ``PostgresStore``.

        This method is idempotent: if already connected, it returns without
        creating a new connection.
        """
        if self._connection is not None:
            return
        self._connection = psycopg.Connection.connect(
            self._db_uri, autocommit=True, prepare_threshold=0
        )
        index = None
        if self._embedding_config:
            index = {
                "dims": self._embedding_config.dims,
                "embed": self._embedding_config.fn,
            }
        self._store = PostgresStore(self._connection, index=index)
        self._store.setup()

    # -------------------------------------------------------------------------------------------- #
    def close(self) -> None:
        """Closes the active connection and releases the store reference."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None
        self._store = None

    # -------------------------------------------------------------------------------------------- #
    #                                       CONTEXT MANAGER                                        #
    # -------------------------------------------------------------------------------------------- #
    def __enter__(self):
        """Enables use of the adapter as a context manager, automatically connecting and closing."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensures the connection is closed when exiting a context block."""
        self.close()
        return False

    # ========================================================================================== #
    #                                    SYNC METHODS                                            #
    # ========================================================================================== #
    def create(self, store_item: StoreItem) -> None:
        """Creates a record from a ``StoreItem`` payload.

        Args:
            store_item: A ``StoreItem`` containing the namespace, key, value,
                and optional index text for the record to create.
        """
        self._require_store().put(
            namespace=store_item.namespace,
            key=store_item.key,
            value=store_item.value,
            index=store_item.index,
        )

    # -------------------------------------------------------------------------------------------- #
    def read(self, namespace: tuple[str, ...], key: str) -> dict | None:
        """Reads a record by key from a namespace.

        Args:
            namespace: Namespace tuple used by the underlying store.
            key: Unique key for the stored record.

        Returns:
            Value dictionary when found, or ``None`` if the key is missing.
        """
        item = self._require_store().get(namespace, key)
        if item is None:
            return None
        return item.value

    # -------------------------------------------------------------------------------------------- #
    def search(
        self,
        namespace: tuple[str, ...],
        filter: dict | None,
        query: str | None,
        limit: int | None = None,
    ) -> list[dict]:
        """Runs metadata and semantic search within a namespace.

        Args:
            namespace: Namespace tuple used by the underlying store.
            filter: Optional dict of metadata fields to filter by
                (e.g. {"source": "news"}).
            query: Query text to compare against indexed embedding text.
            limit: Maximum number of results to return.

        Returns:
            List of value dictionaries returned by the store.
        """
        results = self._require_store().search(
            namespace,
            query=query,
            filter=filter,
            limit=limit,
        )
        return [item.value for item in results]

    # -------------------------------------------------------------------------------------------- #
    def delete(self, namespace: tuple[str, ...], key: str) -> None:
        """Deletes a record by namespace and key.

        Args:
            namespace: Namespace tuple identifying the partition.
            key: Unique key for the stored record.
        """
        self._require_store().delete(namespace, key)

    # -------------------------------------------------------------------------------------------- #
    def exists(self, namespace: tuple[str, ...], key: str) -> bool:
        """Checks whether a same-key record already exists.

        Args:
            namespace: Namespace tuple used by the underlying store.
            key: Unique key for the stored record.

        Returns:
            ``True`` when a matching key is already present, else ``False``.
        """
        result = self._require_store().get(namespace, key)
        return result is not None

    # -------------------------------------------------------------------------------------------- #
    def exists_semantic(
        self,
        namespace: tuple[str, ...],
        query: str,
        threshold: float = DUPLICATE_THRESHOLD,
    ) -> bool:
        """Checks whether a semantically similar record exists.

        Runs embedding search and compares the top result's score against
        the threshold.

        Args:
            namespace: Namespace tuple used by the underlying store.
            query: Query text to compare against indexed embedding text.
            threshold: Minimum similarity score to consider a match.

        Returns:
            ``True`` when a record scores at or above the threshold.
        """
        results = self._require_store().search(
            namespace,
            query=query,
            filter=None,
            limit=1,
        )
        if not results:
            return False
        top = results[0]
        return top.score is not None and top.score >= threshold

    # -------------------------------------------------------------------------------------------- #
    def reset(self, namespace: tuple[str, ...]) -> None:
        """Deletes all items within a given namespace.

        Args:
            namespace: The namespace tuple to clear.
        """
        store = self._require_store()
        items = store.search(namespace, limit=1_000_000)
        if not items:
            return
        confirm = input(f"Delete {len(items)} items from {namespace}? Type YES to confirm: ")
        if confirm != "YES":
            return
        for item in items:
            store.delete(namespace, item.key)

    # -------------------------------------------------------------------------------------------- #
    def count(self, namespace: tuple[str, ...]) -> int:
        """Returns the number of items in a namespace.

        Args:
            namespace: Namespace tuple identifying the partition.

        Returns:
            Number of records in the namespace.
        """
        prefix = ".".join(namespace)
        with self._require_connection().cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM store WHERE prefix = %s",
                (prefix,),
            )
            row = cur.fetchone()
            return int(row[0]) if row is not None else 0

    # -------------------------------------------------------------------------------------------- #
    def _require_store(self) -> PostgresStore:
        """Internal helper to access the connected store instance.

        Raises:
            StoreNotConnectedError: If the store has not been connected.
        """
        if self._store is None:
            raise StoreNotConnectedError
        return self._store

    # -------------------------------------------------------------------------------------------- #
    def _require_connection(self) -> psycopg.Connection:
        """Internal helper to access the connected store instance.

        Raises:
            StoreNotConnectedError: If the store has not been connected.
        """
        if self._connection is None:
            raise StoreNotConnectedError
        return self._connection
