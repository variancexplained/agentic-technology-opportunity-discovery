#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/types                                                                       #
# Filename   : signal.py                                                                           #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Wednesday April 8th 2026 01:31:40 am                                                #
# Modified   : Saturday June 27th 2026 06:11:59 am                                                 #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
"""Signal data models used by the Sciven research pipeline."""

from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

import pydantic
from pydantic import ConfigDict

from sciven.application.discover.score import Score
from sciven.domain import (
    ConsumerMarket,
    DiscontinuityCategory,
    Entity,
    EntityName,
    EntityType,
    Horizontal,
    ProsumerMarket,
    Segment,
    Stage,
    Vertical,
)
from sciven.domain.core import EvidenceType


# ------------------------------------------------------------------------------------------------ #
#                                         SIGNAL SCORE                                             #
# ------------------------------------------------------------------------------------------------ #
@pydantic.dataclasses.dataclass(config=ConfigDict(validate_assignment=True))
class SignalScore(Score):
    """Stores optional per-dimension evaluation scores for a signal.

    Attributes:
        novelty: 1-10. How unprecedented the development is. 1 is a refinement of
            well-trodden ground; 10 has no prior work and opens a new direction.
        magnitude: 1-10. Quantification of the magnitude of the signal.
        economic: 1-10. Plausible scale of value creation or destruction enabled.
            1 is niche with no clear commercial pathway; 10 could create or destroy
            $1B+ in addressable market within roughly 5 years.
        feasibility: 1-10. Degree to which signal exploitation is feasible for an
            agent-backed solopreneur within a ~6-10 month horizon, considering
            technical complexity, required resources, and competitive landscape.
            1 is infeasible for any actor; 10 is straightforward for a solo
            founder with current capabilities and resources.
        evidence: 1-10. Strength and authoritativeness of the supporting source.
            1 is anonymous or promotional with no third-party validation; 10 is
            peer-reviewed publication, primary release with reproducible metrics,
            or official filing with multi-source corroboration.
        generality: 1-10. Breadth of applicability across domains, stages, or use
            cases. 1 is narrow single-application; 10 is a horizontal capability
            that travels across many problem types.

    Examples:
        Instantiate a partially populated signal score:

        >>> score = SignalScore(novelty=8, magnitude=9, evidence=7)
        >>> score.novelty
        8

        Instantiate an empty signal score to populate during later review:

        >>> score = SignalScore()
        >>> score.economic is None
        True
    """


# ================================================================================================ #
#                                       BASE SIGNAL                                                #
# ================================================================================================ #
@dataclass(kw_only=True)
class Signal(Entity):
    """Represents a normalized research signal used across discovery workflows.

    Attributes:
        name: Short, human-readable title for the signal.
        description: Detailed narrative describing the signal and implications.
        entity_name: High-level category for the signal (for example, innovation or market).
        signal_date: Date the signal event occurred, if known.
        score: Multi-dimensional evaluation score for this signal.
        tags: Free-form tags used for organization and retrieval.
        stage: Pipeline stage associated with the signal.
        entity_type: Entity type discriminator for signal records.
        run_id: Identifier of the run that produced the signal.
        search_id: Identifier of the search operation that found this signal.
        source_id: Identifier of the source document.
        document_id: Identifier of the source document supporting this signal.

    Examples:
        >>> signal = InnovationSignal(
        ...     id="signal-1",
        ...     name="GPT-5 Release",
        ...     description="OpenAI releases GPT-5 with significant capability improvements.",
        ...     discontinuity_category=DiscontinuityCategory.CAPABILITY_FRONTIER,
        ...     discontinuity_claim="GPT-5 materially improves model reasoning.",
        ...     evidence_type=EvidenceType.INNOVATION,
        ...     run_id="run-1",
        ...     search_id="search-1",
        ...     source_id="source-1",
        ...     document_id="doc-1",
        ...     agent_name="system",
        ... )
        >>> signal.name
        'GPT-5 Release'
    """

    name: str
    description: str
    signal_date: datetime | None = None
    score: SignalScore | None = None

    # Administrative fields
    stage: Stage = field(default=Stage.DISCOVERY)
    entity_type: EntityType = field(default=EntityType.SIGNAL)
    entity_name: EntityName
    evidence_type: EvidenceType
    tags: list[str] = field(default_factory=list)

    # Lineage
    run_id: str
    search_id: str
    source_id: str
    document_id: str

    @property
    def embedding_text(self) -> str:
        """Returns text used to embed venture-capital signals.

        Returns:
            Name and description joined for semantic indexing.

        Examples:
            >>> signal = InnovationSignal(
            ...     id="signal-1",
            ...     name="GPT-5 Release",
            ...     description="OpenAI releases GPT-5 with significant capability improvements.",
            ...     discontinuity_category=DiscontinuityCategory.CAPABILITY_FRONTIER,
            ...     discontinuity_claim="GPT-5 materially improves model reasoning.",
            ...     run_id="run-1",
            ...     search_id="search-1",
            ...     source_id="source-1",
            ...     document_id="doc-1",
            ...     agent_name="system",
            ... )
            >>> signal.embedding_text
            'GPT-5 Release OpenAI releases GPT-5 with significant capability improvements.'
        """
        return f"{self.name} {self.description}"

    @classmethod
    @abstractmethod
    def create(cls, data: dict) -> Signal:
        """Abstract Factory method to create a Signal instance from a dictionary.

        Concrete subclasses must override this method to provide type-specific
        deserialization logic. The base implementation dispatches to the appropriate
        subclass based on the signal type.

        Args:
            data: A dictionary containing the signal fields, typically retrieved from storage.

        Returns:
            A hydrated Signal subclass instance.

        Raises:
            ValueError: If the signal type is not supported or data is invalid.

        Examples:
            >>> payload = {
            ...     "id": "signal-1",
            ...     "name": "GPT-5 Release",
            ...     "description": "OpenAI releases GPT-5 with capability improvements.",
            ...     "entity_name": "innovation_signal",
            ...     "discontinuity_category": "capability_frontier",
            ...     "discontinuity_claim": "GPT-5 advances reasoning capability.",
            ...     "run_id": "run-1",
            ...     "search_id": "search-1",
            ...     "source_id": "source-1",
            ...     "document_id": "doc-1",
            ...     "agent_name": "system",
            ...     "stage": "discovery",
            ...     "entity_type": "signal",
            ...     "created": "2026-04-08T01:31:40",
            ...     "modified": None,
            ... }
            >>> signal = Signal.create(payload)
            >>> isinstance(signal, InnovationSignal)
            True
        """
        subclass = ENTITY_NAME_MAP.get(EntityName.from_value(data["entity_name"]))
        if not subclass:
            raise ValueError(f"Unsupported entity name: {data.get('entity_name')}")
        return subclass.create(data)


# ================================================================================================ #
#                                       INNOVATION SIGNAL                                          #
# ================================================================================================ #
@dataclass(kw_only=True)
class InnovationSignal(Signal):
    """Represents an innovation-type signal capturing a technology discontinuity.

    Extends :class:`Signal` with fields that describe the nature and claim of
    the observed discontinuity.

    Attributes:
        discontinuity_category: Category describing the type of discontinuity observed.
        discontinuity_claim: Claim summarizing the expected discontinuity impact.

    Examples:
        >>> innovation = InnovationSignal(
        ...     id="signal-1",
        ...     name="Quantum Computing Breakthrough",
        ...     description="A new quantum algorithm demonstrates practical advantage.",
        ...     discontinuity_category=DiscontinuityCategory.CAPABILITY_FRONTIER,
        ...     discontinuity_claim="Quantum computers enable optimization problems.",
        ...     evidence_type=EvidenceType.INNOVATION,
        ...     run_id="run-1",
        ...     search_id="search-1",
        ...     source_id="source-1",
        ...     document_id="doc-1",
        ...     agent_name="system",
        ... )
        >>> innovation.entity_name
        <EntityName.INNOVATION_SIGNAL: 'innovation_signal'>
    """

    discontinuity_category: DiscontinuityCategory
    discontinuity_claim: str
    entity_name: EntityName = field(default=EntityName.INNOVATION_SIGNAL)
    evidence_type: EvidenceType = field(default=EvidenceType.INNOVATION)

    @classmethod
    def create(cls, data: dict) -> InnovationSignal:
        """Factory method to create an InnovationSignal instance from a dictionary.

        Args:
            data: Serialized signal payload containing primitive values, serialized
                enums, nested score/document dictionaries, and optional metadata fields.

        Returns:
            A hydrated InnovationSignal instance with normalized enums and datetimes.

        Raises:
            KeyError: If required keys are missing from ``data``.
            ValueError: If enum values or ISO datetime strings are invalid.

        Examples:
            >>> payload = {
            ...     "id": "signal-1",
            ...     "name": "Quantum Computing Breakthrough",
            ...     "description": "A new quantum algorithm demonstrates practical advantage.",
            ...     "entity_name": "innovation_signal",
            ...     "discontinuity_category": "capability_frontier",
            ...     "discontinuity_claim": "Quantum computers enable optimization problems.",
            ...     "evidence_type": "innovation",
            ...     "run_id": "run-1",
            ...     "search_id": "search-1",
            ...     "source_id": "source-1",
            ...     "document_id": "doc-1",
            ...     "agent_name": "system",
            ...     "stage": "discovery",
            ...     "entity_type": "signal",
            ...     "created": "2026-04-08T01:31:40",
            ...     "modified": None,
            ... }
            >>> signal = InnovationSignal.create(payload)
            >>> signal.name
            'Quantum Computing Breakthrough'
        """
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            signal_date=(
                datetime.fromisoformat(data["signal_date"]) if data.get("signal_date") else None
            ),
            discontinuity_category=DiscontinuityCategory.from_value(data["discontinuity_category"]),
            discontinuity_claim=data["discontinuity_claim"],
            evidence_type=EvidenceType.from_value(data["evidence_type"]),
            score=SignalScore(**data["score"]) if data.get("score") else None,
            tags=data.get("tags", []),
            agent_name=data.get("agent_name"),
            run_id=data["run_id"],
            search_id=data["search_id"],
            source_id=data["source_id"],
            document_id=data["document_id"],
            stage=Stage.from_value(data["stage"]),
            entity_type=EntityType.from_value(data["entity_type"]),
            entity_name=EntityName.from_value(data["entity_name"]),
            created=datetime.fromisoformat(data["created"]),
            modified=datetime.fromisoformat(data["modified"]) if data.get("modified") else None,
        )


# ================================================================================================ #
#                                     MARKET SIGNAL                                                #
# ================================================================================================ #
@dataclass(kw_only=True)
class MarketSignal(Signal):
    """Represents a market-type signal capturing commercial or demand dynamics.

    Extends :class:`Signal` with fields that characterize the relevant market
    context and competitive landscape.

    Attributes:
        market_segment: Market segment classification for market-related signals.
        market_vertical: Industry vertical classification for market-related signals.
        market_horizontal: Cross-functional business area classification.
        market_consumer: Consumer market classification when applicable.
        market_prosumer: Prosumer market classification when applicable.
        market_size_estimate: Estimated market size, if available.
        market_demand: Summary of demand-side dynamics.
        market_competition: Summary of competitive landscape dynamics.

    Examples:
        >>> market = MarketSignal(
        ...     id="signal-1",
        ...     name="Enterprise AI Adoption",
        ...     description="Fortune 500 companies rapidly deploying AI systems.",
        ...     market_segment=Segment.ENTERPRISE,
        ...     market_vertical=Vertical.PROFESSIONAL_SERVICES,
        ...     evidence_type=EvidenceType.MARKET,
        ...     market_size_estimate=5000000000.0,
        ...     market_demand="Increased demand for AI infrastructure and services.",
        ...     run_id="run-1",
        ...     search_id="search-1",
        ...     source_id="source-1",
        ...     document_id="doc-1",
        ...     agent_name="system",
        ... )
        >>> market.entity_name
        <EntityName.MARKET_SIGNAL: 'market_signal'>
    """

    entity_name: EntityName = field(default=EntityName.MARKET_SIGNAL)
    evidence_type: EvidenceType = field(default=EvidenceType.MARKET)

    # Market and application fields
    market_segment: Segment | None = None
    market_vertical: Vertical | None = None
    market_horizontal: Horizontal | None = None
    market_consumer: ConsumerMarket | None = None
    market_prosumer: ProsumerMarket | None = None
    market_size_estimate: float | None = None
    market_demand: str | None = None
    market_competition: str | None = None

    @classmethod
    def create(cls, data: dict) -> MarketSignal:
        """Constructs a market signal instance from a raw dictionary payload.

        Args:
            data: Raw signal payload containing primitive values,
                serialized enums, nested score/document dictionaries,
                and optional metadata fields.

        Returns:
            Hydrated signal model with normalized enums and datetimes.

        Raises:
            KeyError: If required keys are missing from ``data``.
            ValueError: If enum values or ISO datetime strings are invalid.

        Examples:
            >>> payload = {
            ...     "id": "signal-1",
            ...     "name": "Enterprise AI Adoption",
            ...     "description": "Fortune 500 companies rapidly deploying AI systems.",
            ...     "entity_name": "market_signal",
            ...     "market_segment": "enterprise",
            ...     "market_vertical": "professional_services",
            ...     "market_size_estimate": 5000000000.0,
            ...     "market_demand": "Increased demand for AI infrastructure.",
            ...     "evidence_type": "market",
            ...     "run_id": "run-1",
            ...     "search_id": "search-1",
            ...     "source_id": "source-1",
            ...     "document_id": "doc-1",
            ...     "agent_name": "system",
            ...     "stage": "discovery",
            ...     "entity_type": "signal",
            ...     "created": "2026-04-08T01:31:40",
            ...     "modified": None,
            ... }
            >>> signal = MarketSignal.create(payload)
            >>> signal.name
            'Enterprise AI Adoption'
        """
        return cls(
            name=data["name"],
            description=data["description"],
            score=SignalScore(**data["score"]) if data.get("score") else None,
            signal_date=(
                datetime.fromisoformat(data["signal_date"]) if data.get("signal_date") else None
            ),
            market_segment=Segment.from_value(data["market_segment"])
            if data.get("market_segment")
            else None,
            market_vertical=Vertical.from_value(data["market_vertical"])
            if data.get("market_vertical")
            else None,
            market_horizontal=Horizontal.from_value(data["market_horizontal"])
            if data.get("market_horizontal")
            else None,
            market_consumer=ConsumerMarket.from_value(data["market_consumer"])
            if data.get("market_consumer")
            else None,
            market_prosumer=ProsumerMarket.from_value(data["market_prosumer"])
            if data.get("market_prosumer")
            else None,
            market_size_estimate=data.get("market_size_estimate"),
            market_demand=data.get("market_demand"),
            market_competition=data.get("market_competition"),
            evidence_type=EvidenceType.from_value(data["evidence_type"]),
            tags=data.get("tags", []),
            agent_name=data.get("agent_name"),
            id=data.get("id"),
            run_id=data["run_id"],
            search_id=data["search_id"],
            source_id=data["source_id"],
            document_id=data["document_id"],
            stage=Stage.from_value(data["stage"]),
            entity_type=EntityType.from_value(data["entity_type"]),
            entity_name=EntityName.from_value(data["entity_name"]),
            created=datetime.fromisoformat(data["created"]),
            modified=datetime.fromisoformat(data["modified"]) if data.get("modified") else None,
        )


# ================================================================================================ #
#                                    ACQUISITION SIGNAL                                            #
# ================================================================================================ #
@dataclass(kw_only=True)
class AcquisitionSignal(Signal):
    """Represents an acquisition-type signal indicating potential M&A intent.

    Extends :class:`Signal` with fields that describe the prospective acquirer
    and the strategic rationale behind the acquisition.

    Attributes:
        acquirer: Name of the potential acquiring entity.
        need: The strategic capability or technology gap driving the acquisition.
        need_horizon: Expected timeframe within which the need must be addressed.
        buy_justification: Reasoning for why the acquirer would buy rather than build.

    Examples:
        >>> acquisition = AcquisitionSignal(
        ...     id="signal-1",
        ...     name="Google Acquires AI Startup",
        ...     description="Google acquires a specialized AI research company.",
        ...     acquirer="Google",
        ...     need="Advanced reasoning capabilities for search.",
        ...     need_horizon="2026",
        ...     buy_justification="Faster to acquire than build internal expertise.",
        ...     evidence_type=EvidenceType.ACQUISITION,
        ...     run_id="run-1",
        ...     search_id="search-1",
        ...     source_id="source-1",
        ...     document_id="doc-1",
        ...     agent_name="system",
        ... )
        >>> acquisition.acquirer
        'Google'
    """

    acquirer: str
    need: str
    need_horizon: str
    buy_justification: str
    entity_name: EntityName = field(default=EntityName.ACQUISITION_SIGNAL)
    evidence_type: EvidenceType = field(default=EvidenceType.ACQUISITION)

    @property
    def embedding_text(self) -> str:
        """Returns text used to embed venture-capital signals.

        Returns:
            Name, acquirer, need, horizon, justification, and description joined
            for semantic indexing.

        Examples:
            >>> acquisition = AcquisitionSignal(
            ...     id="signal-1",
            ...     name="Google Acquires AI Startup",
            ...     description="Google acquires a specialized AI research company.",
            ...     acquirer="Google",
            ...     need="Advanced reasoning capabilities for search.",
            ...     need_horizon="2026",
            ...     buy_justification="Faster to acquire than build internal expertise.",
            ...     evidence_type=EvidenceType.ACQUISITION,
            ...     run_id="run-1",
            ...     search_id="search-1",
            ...     source_id="source-1",
            ...     document_id="doc-1",
            ...     agent_name="system",
            ... )
            >>> "Google" in acquisition.embedding_text
            True
        """
        return f"{self.name} {self.acquirer} {self.need} {self.need_horizon} {self.buy_justification} {self.description}"

    @classmethod
    def create(cls, data: dict) -> AcquisitionSignal:
        """Constructs an AcquisitionSignal instance from a raw dictionary payload.

        Args:
            data: Raw signal payload containing primitive values,
                serialized enums, nested score/document dictionaries,
                and optional metadata fields.

        Returns:
            Hydrated AcquisitionSignal with normalized enums and datetimes.

        Raises:
            KeyError: If required keys are missing from ``data``.
            ValueError: If enum values or ISO datetime strings are invalid.

        Examples:
            >>> payload = {
            ...     "id": "signal-1",
            ...     "name": "Google Acquires AI Startup",
            ...     "description": "Google acquires a specialized AI research company.",
            ...     "entity_name": "acquisition_signal",
            ...     "acquirer": "Google",
            ...     "need": "Advanced reasoning capabilities for search.",
            ...     "need_horizon": "2026",
            ...     "buy_justification": "Faster to acquire than build internal expertise.",
            ...     "evidence_type": "acquisition",
            ...     "run_id": "run-1",
            ...     "search_id": "search-1",
            ...     "source_id": "source-1",
            ...     "document_id": "doc-1",
            ...     "agent_name": "system",
            ...     "stage": "discovery",
            ...     "entity_type": "signal",
            ...     "created": "2026-04-08T01:31:40",
            ...     "modified": None,
            ... }
            >>> signal = AcquisitionSignal.create(payload)
            >>> signal.acquirer
            'Google'
        """
        return cls(
            name=data["name"],
            description=data["description"],
            document_id=data["document_id"],
            score=SignalScore(**data["score"]) if data.get("score") else None,
            signal_date=(
                datetime.fromisoformat(data["signal_date"]) if data.get("signal_date") else None
            ),
            acquirer=data["acquirer"],
            need=data["need"],
            need_horizon=data["need_horizon"],
            buy_justification=data["buy_justification"],
            evidence_type=EvidenceType.from_value(data["evidence_type"]),
            tags=data.get("tags", []),
            agent_name=data.get("agent_name"),
            id=data.get("id"),
            run_id=data["run_id"],
            search_id=data["search_id"],
            source_id=data["source_id"],
            stage=Stage.from_value(data["stage"]),
            entity_type=EntityType.from_value(data["entity_type"]),
            entity_name=EntityName.from_value(data["entity_name"]),
            created=datetime.fromisoformat(data["created"]),
            modified=datetime.fromisoformat(data["modified"]) if data.get("modified") else None,
        )


# ------------------------------------------------------------------------------------------------ #
#                                   SIGNAL TYPE REGISTRY                                         #
# ------------------------------------------------------------------------------------------------ #
ENTITY_NAME_MAP: dict[EntityName, type[Signal]] = {
    EntityName.INNOVATION_SIGNAL: InnovationSignal,
    EntityName.MARKET_SIGNAL: MarketSignal,
    EntityName.ACQUISITION_SIGNAL: AcquisitionSignal,
}
