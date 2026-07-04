#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Description: The Science of Venture Development                                                  #
# Version    : 0.1.1                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/repos                                                                       #
# Filename   : document.py                                                                         #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Saturday May 2nd 2026 12:56:52 am                                                   #
# Modified   : Monday June 29th 2026 10:04:08 am                                                   #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #

"""Document repository for the Sciven research pipeline."""

import logging

from sciven.domain import EntityType, Stage
from sciven.domain.document import Document, DocumentFormat
from sciven.infra.persistence.repo.base import Repo

# ------------------------------------------------------------------------------------------------ #
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------------------------ #
#                                 DOCUMENT REPOSITORY                                              #
# ------------------------------------------------------------------------------------------------ #
class DocumentRepo(Repo[Document]):
    """Repository for persisting and retrieving Document domain objects.

    Args:
        adapter: Store adapter used for persistence and search operations.

    Examples:
        >>> from sciven.adapters.langgraph.store import StoreAdapter
        >>> adapter = StoreAdapter()
        >>> repo = DocumentRepo(adapter=adapter)
    """

    # ============================================================================================ #
    #                                 IS DUPLICATE                                                 #
    # ============================================================================================ #
    def exists(self, item: Document, **kwargs) -> bool:
        """Determines if a document is a duplicate.

        Uses a three-tier strategy, returning True at the first match:

        1. Exact key match in the namespace.
        2. Exact URL match via metadata filter. Catches re-ingest under a
        different id, e.g. when a publisher changes the headline after
        publishing.
        3. Exact title match via metadata filter. Catches syndicated reposts
        on different domains where the URL differs but the title is
        preserved.

        Args:
            item: The document to check for duplication.
            **kwargs: Additional keyword arguments (unused).

        Returns:
            True if the document is a duplicate, False otherwise.
        """
        # Tier 1: exact key
        if self._adapter.exists(item.namespace, item.key):
            return True

        # Tier 2: exact URL (post-normalize_url)
        if item.url:
            url_matches = self._adapter.search(
                item.namespace,
                filter={"url": item.url},
                query=None,
                limit=1,
            )
            if url_matches:
                return True

        # Tier 3: exact title
        if item.title:
            title_matches = self._adapter.search(
                item.namespace,
                filter={"title": item.title},
                query=None,
                limit=1,
            )
            if title_matches:
                return True

        return False

    # -------------------------------------------------------------------------------------------- #
    def deserialize(self, data: dict) -> Document:
        """Deserializes a value dictionary to a Document instance.

        Args:
            data: Value dictionary containing a ``entity_name`` field used to
                dispatch to the correct Document subclass.

        Returns:
            A Document instance.
        """
        return Document.create(data)

    # -------------------------------------------------------------------------------------------- #
    def deserialize_batch(self, items: list[dict]) -> list[Document]:
        """Deserializes a list of value dictionaries to Document instances.

        Silently skips items that fail deserialization and logs the error.

        Args:
            items: List of value dictionaries to deserialize.

        Returns:
            List of successfully deserialized Document instances.
        """
        documents: list[Document] = []
        for data in items:
            try:
                documents.append(self.deserialize(data))
            except (ValueError, KeyError) as exc:
                logger.warning("Failed to deserialize document: %s", exc)
        return documents

    # -------------------------------------------------------------------------------------------- #
    def summary(self, limit: int = 1_000_000) -> dict[str, int]:
        """Counts documents by format within the discover/document namespace.

        Args:
            limit: Maximum number of documents to fetch from storage.

        Returns:
            Dictionary mapping each ``DocumentFormat`` value to its count,
            plus a trailing ``total`` entry.
        """
        namespace = (Stage.DISCOVERY.value, EntityType.DOCUMENT.value)
        documents = self.search(namespace, limit=limit)

        formats = list(DocumentFormat)

        total = 0
        totals_by_format = {fmt.value: 0 for fmt in formats}

        for document in documents:
            total += 1
            totals_by_format[document.document_format.value] += 1

        summary = {fmt.value: totals_by_format[fmt.value] for fmt in formats}
        summary["total"] = total

        return summary
