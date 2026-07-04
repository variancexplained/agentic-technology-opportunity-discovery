#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/adapters                                                                    #
# Filename   : base.py                                                                             #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Tuesday April 8th 2026                                                              #
# Modified   : Monday June 29th 2026 08:06:03 am                                                   #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
"""Store models and adapter helpers for LangGraph Postgres stores."""

from abc import ABC, abstractmethod
from typing import Any


# ================================================================================================ #
#                                    PERSISTENCE ADAPTER                                           #
# ================================================================================================ #
class PersistenceAdapter(ABC):
    """Abstract base class for persistence adapters.

    Subclasses implement lifecycle and CRUD operations for a concrete
    persistence backend.

    """

    # -------------------------------------------------------------------------------------------- #
    #                                       CONNECTION                                             #
    # -------------------------------------------------------------------------------------------- #
    @abstractmethod
    def connect(self) -> None:
        """Connect the adapter to the underlying persistence backend."""

    # -------------------------------------------------------------------------------------------- #
    @abstractmethod
    def close(self) -> None:
        """Close the connection to the underlying persistence backend."""

    # -------------------------------------------------------------------------------------------- #
    #                                       CONTEXT MANAGER                                        #
    # -------------------------------------------------------------------------------------------- #
    def __enter__(self):
        """Enter a context-managed adapter session.

        Returns:
            PersistenceAdapter: The connected adapter instance.
        """
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit a context-managed adapter session.

        Args:
            exc_type: Exception type raised in the context, if any.
            exc_val: Exception instance raised in the context, if any.
            exc_tb: Traceback associated with the exception, if any.

        Returns:
            bool: False to propagate any exception from the context block.
        """
        self.close()
        return False

    # ========================================================================================== #
    #                                    SYNC METHODS                                            #
    # ========================================================================================== #
    @abstractmethod
    def create(self, *args, **kwargs) -> None:
        """Create a record in the underlying persistence store."""

    # -------------------------------------------------------------------------------------------- #
    @abstractmethod
    def read(self, *args, **kwargs) -> Any | None:
        """Read a record from the underlying persistence store.

        Returns:
            Any | None: The retrieved record if found, otherwise None.
        """

    # -------------------------------------------------------------------------------------------- #
    @abstractmethod
    def delete(self, *args, **kwargs) -> None:
        """Delete a record from the underlying persistence store."""

    # -------------------------------------------------------------------------------------------- #
    @abstractmethod
    def exists(self, *args, **kwargs) -> bool:
        """Check whether a same-key record already exists.

        Returns:
            bool: True when a matching record exists, else False.
        """
