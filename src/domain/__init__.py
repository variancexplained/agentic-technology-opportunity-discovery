#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/domain                                                                      #
# Filename   : __init__.py                                                                         #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Tuesday April 7th 2026 09:16:34 pm                                                  #
# Modified   : Sunday June 14th 2026 08:44:18 pm                                                   #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
"""Public API for the Sciven domain package.

Core types, base classes, and enumerations are defined in ``sciven.domain.core``
and re-exported here so that ``from sciven.domain import Entity`` (and every other
core symbol) continues to resolve. This module is a thin façade: it adds no
behavior of its own.
"""

from sciven.domain.core import (
    IMMUTABLE_TYPES,
    NUMERICS,
    SEQUENCE_TYPES,
    ConsumerMarket,
    DataClass,
    DiscontinuityCategory,
    Entity,
    EntityName,
    EntityType,
    EnumClass,
    EvidenceType,
    Horizontal,
    ProsumerMarket,
    Segment,
    SignalAmplifier,
    SourceID,
    Stage,
    TaskType,
    Vertical,
)

__all__ = [
    "IMMUTABLE_TYPES",
    "NUMERICS",
    "SEQUENCE_TYPES",
    "ConsumerMarket",
    "DataClass",
    "DiscontinuityCategory",
    "Entity",
    "EntityName",
    "EntityType",
    "EnumClass",
    "EvidenceType",
    "Horizontal",
    "ProsumerMarket",
    "Segment",
    "SignalAmplifier",
    "SourceID",
    "Stage",
    "TaskType",
    "Vertical",
]
