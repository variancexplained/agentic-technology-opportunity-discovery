#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/repos                                                                       #
# Filename   : signal.py                                                                           #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Monday April 13th 2026                                                              #
# Modified   : Monday June 29th 2026 06:49:31 am                                                   #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
"""Signal repository for the Sciven research pipeline."""

import logging

from sciven.domain import EntityType, Stage
from sciven.domain.signal import Signal
from sciven.infra.persistence.repo.base import Repo

logger = logging.getLogger(__name__)

# ================================================================================================ #
#                                SIGNAL REPOSITORY                                                 #
# ================================================================================================ #


class SignalRepo(Repo[Signal]):
    """Repository implementation for persisting and hydrating signal records.

    Args:
        adapter: Store adapter used for persistence and search operations.

    Examples:
        >>> from sciven.adapters.langgraph.store import StoreAdapter
        >>> adapter = StoreAdapter()
        >>> repo = SignalRepo(adapter=adapter)
    """

    # -------------------------------------------------------------------------------------------- #
    def deserialize(self, data: dict) -> Signal:
        """Builds a signal instance from a serialized payload.

        Reads the ``entity_name`` discriminator and dispatches to the matching
        concrete subclass via ``Signal.create`` and the ``SIGNAL_TYPE_MAP``
        registry in ``sciven.types.signal``.

        Args:
            data: Serialized signal payload containing a ``entity_name`` discriminator.

        Returns:
            Deserialized Signal subclass instance for the provided signal type.

        Raises:
            KeyError: If ``entity_name`` (or another required field) is missing.
            ValueError: If ``entity_name`` is not a supported value.
        """
        return Signal.create(data)

    # -------------------------------------------------------------------------------------------- #
    def deserialize_batch(self, items: list[dict]) -> list[Signal]:
        """Builds signal instances from serialized payloads.

        Silently skips items that fail deserialization and logs the error.

        Args:
            items: Serialized signal payloads to deserialize.

        Returns:
            List of successfully deserialized ``Signal`` instances.
        """
        results: list[Signal] = []
        for data in items:
            try:
                results.append(self.deserialize(data))
            except (ValueError, KeyError) as exc:
                logger.warning("Failed to deserialize signal: %s", exc)
        return results

    # -------------------------------------------------------------------------------------------- #
    def summary(self, limit: int = 1_000_000) -> dict:
        """Summarizes signals across type and discontinuity category.

        Args:
            limit: Upper bound on signals fetched. Defaults to 100000.

        Returns:
            Dictionary with total, avg_score, and breakdowns by
            entity_name and discontinuity_category (count and avg_score each).
            Only ``InnovationSignal`` carries a discontinuity category, so the
            ``by_discontinuity_category`` breakdown reflects innovation signals
            alone; market and acquisition signals contribute to ``total``,
            ``avg_score``, and ``by_entity_name`` only.
        """
        namespace = (Stage.DISCOVERY.value, EntityType.SIGNAL.value)
        signals = self.search(namespace, limit=limit)

        total = len(signals)
        if total == 0:
            return {
                "total": 0,
                "avg_score": 0.0,
                "by_entity_name": {},
            }

        sum_score = 0.0
        by_entity_name: dict[str, dict] = {}

        for s in signals:
            sc = s.score.score if s.score else 0.0
            sum_score += sc

            st = s.entity_name.value
            if st not in by_entity_name:
                by_entity_name[st] = {"count": 0, "sum_score": 0.0}
            by_entity_name[st]["count"] += 1
            by_entity_name[st]["sum_score"] += sc

        return {
            "total": total,
            "avg_score": sum_score / total,
            "by_entity_name": {
                k: {"count": v["count"], "avg_score": v["sum_score"] / v["count"]}
                for k, v in by_entity_name.items()
            },
        }
