#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Description: Sciven: The Science of Venture Development                                          #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/infra/persistence/provider                                                  #
# Filename   : langfuse.py                                                                         #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Monday June 29th 2026 08:07:40 am                                                   #
# Modified   : Monday June 29th 2026 12:45:02 pm                                                   #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
"""Langfuse persistence adapter."""

from datetime import datetime

from langfuse import Langfuse, get_client
from langfuse.api.prompts.types.prompt_meta import PromptMeta
from langfuse.model import TextPromptClient

from sciven.infra.persistence.provider.base import PersistenceAdapter


# ------------------------------------------------------------------------------------------------ #
class LangfuseAdapter(PersistenceAdapter):
    """Persistence adapter backed by Langfuse prompt management.

    Implements the :class:`PersistenceAdapter` CRUD/lifecycle contract against
    the Langfuse prompt store. Records are :class:`Prompt` objects: ``create``
    registers a new prompt version, ``read`` fetches (and optionally compiles)
    a stored prompt, and ``exists`` checks for presence by name. ``delete`` is
    not supported by the Langfuse prompt API and raises ``NotImplementedError``.

    The adapter is usable as a context manager via the inherited
    ``__enter__``/``__exit__``, which call :meth:`connect` and :meth:`close`.
    """

    def __init__(self):
        """Initialize the adapter.

        The Langfuse client is declared here but not instantiated until
        :meth:`connect` is called.
        """
        # Annotation only — the live client is assigned in connect().
        self._client: Langfuse

    # -------------------------------------------------------------------------------------------- #

    def connect(self) -> None:
        """Connect to Langfuse.

        Resolves the configured Langfuse client via ``get_client()`` (which
        reads credentials/host from the environment) and caches it on the
        adapter for subsequent operations.
        """
        self._client = get_client()

    # -------------------------------------------------------------------------------------------- #
    def close(self) -> None:
        """Close the connection.

        No-op: the Langfuse client manages its own HTTP session and requires
        no explicit teardown, but the method is provided to satisfy the
        :class:`PersistenceAdapter` lifecycle contract.
        """

    # -------------------------------------------------------------------------------------------- #
    def create(self, name: str, content: str, labels: list[str] | None = None) -> None:
        """Register a new prompt version in Langfuse.

        Args:
            name (str): The name of the prompt.
            content (str): The content of the prompt.
            labels (list[str] | None): Optional labels for the prompt.

        """
        self._client.create_prompt(name=name, prompt=content, labels=labels or [])

    # -------------------------------------------------------------------------------------------- #
    def read(
        self,
        name: str,
        version: int | None = None,
        label: str | None = None,
        cache_ttl_seconds: int | None = None,
        max_retries: int | None = None,
        fetch_timeout_seconds: int | None = None,
    ) -> TextPromptClient:
        """Fetch a stored prompt.

        Args:
            name (str): Name of the prompt to retrieve.
            version (int | None): Specific prompt version to fetch.
            label (str | None): Label (e.g. ``"production"``) to resolve.
            cache_ttl_seconds (int | None): Client-side cache TTL for the fetch.
            max_retries (int | None): Maximum fetch retries.
            fetch_timeout_seconds (int | None): Per-request fetch timeout.

        Returns:
            TextPromptClient: The prompt instance.
        """
        try:
            return self._client.get_prompt(
                name=name,
                version=version,
                label=label,
                cache_ttl_seconds=cache_ttl_seconds,
                max_retries=max_retries,
                fetch_timeout_seconds=fetch_timeout_seconds,
            )

        except Exception as e:
            raise RuntimeError(f"Failed to read prompt '{name}': {e}") from e

    # -------------------------------------------------------------------------------------------- #

    def delete(self, name: str, label: str | None = None, version: int | None = None) -> None:
        """Delete a prompt.

        Args:
            name (str): Name of the prompt to delete.
            label (str | None): Optional label of the prompt to delete.
            version (int | None): Optional version of the prompt to delete.
        """
        self._client.api.prompts.delete(prompt_name=name, label=label, version=version)

    # -------------------------------------------------------------------------------------------- #
    def list_prompts(
        self,
        name: str | None = None,
        label: str | None = None,
        tag: str | None = None,
        page: int | None = None,
        limit: int | None = None,
        from_updated_at: datetime | None = None,
        to_updated_at: datetime | None = None,
    ) -> list[PromptMeta]:
        """List all prompts in Langfuse.

        Returns:
            list[PromptMeta]: List of prompt instances.
        """
        return self._client.api.prompts.list(
            name=name,
            label=label,
            tag=tag,
            page=page,
            limit=limit,
            from_updated_at=from_updated_at,
            to_updated_at=to_updated_at,
        ).data

    # -------------------------------------------------------------------------------------------- #

    def exists(
        self,
        name: str,
        version: int | None = None,
        label: str | None = None,
        cache_ttl_seconds: int | None = None,
        max_retries: int | None = None,
        fetch_timeout_seconds: int | None = None,
    ) -> bool:
        """Check whether a prompt exists by attempting to read it.

        Delegates to :meth:`read`; any exception raised while fetching (e.g. the
        prompt not being found) is treated as "does not exist".

        Args:
            name (str): Name of the prompt to check.
            version (int | None): Specific prompt version to check.
            label (str | None): Label to resolve.
            cache_ttl_seconds (int | None): Client-side cache TTL for the fetch.
            max_retries (int | None): Maximum fetch retries.
            fetch_timeout_seconds (int | None): Per-request fetch timeout.

        Returns:
            bool: True if a matching prompt was retrieved, else False.
        """
        try:
            prompt = self.read(
                name=name,
                version=version,
                label=label,
                cache_ttl_seconds=cache_ttl_seconds,
                max_retries=max_retries,
                fetch_timeout_seconds=fetch_timeout_seconds,
            )
            return prompt is not None
        except Exception:
            return False
