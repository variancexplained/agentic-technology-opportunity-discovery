#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/domain                                                                      #
# Filename   : core.py                                                                             #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Tuesday April 7th 2026 09:16:34 pm                                                  #
# Modified   : Tuesday June 30th 2026 11:04:19 pm                                                  #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #

"""Core types, base classes, and enumerations for the Sciven research platform."""

from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid7

import numpy as np

IMMUTABLE_TYPES: tuple = (
    str,
    int,
    float,
    bool,
    np.int16,
    np.int32,
    np.int64,
    np.int8,
    np.float16,
    np.float32,
    np.float64,
    np.float128,
)
SEQUENCE_TYPES: tuple = (
    list,
    tuple,
)

NUMERICS = [
    "int16",
    "int32",
    "int64",
    "float16",
    "float32",
    "float64",
    np.int16,
    np.int32,
    np.int64,
    np.int8,
    np.float16,
    np.float32,
    np.float64,
    np.float128,
]


# ------------------------------------------------------------------------------------------------ #
#                                         DATA CLASS                                               #
# ------------------------------------------------------------------------------------------------ #
@dataclass
class DataClass:
    """Base dataclass with enhanced representation and export methods.

    Provides serialization and formatting utilities for all subclasses.

    Attributes:
        None.

    Examples:
        >>> data = DataClass()
        >>> isinstance(data, DataClass)
        True
    """

    def __repr__(self) -> str:
        """Returns a string representation of the object for debugging.

        Includes only fields with immutable types (str, int, float, bool, numpy numeric types).

        Returns:
            String representation suitable for debugging output.
        """
        s = "{}({})".format(
            self.__class__.__name__,
            ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items() if type(v) in IMMUTABLE_TYPES),
        )
        return s

    def __str__(self) -> str:
        """Returns a formatted string representation.

        Produces a centered, columnar display of immutable fields suitable for console output.

        Returns:
            Formatted multiline string for display.
        """
        width = 32
        breadth = width * 2
        s = f"\n\n{self.__class__.__name__.center(breadth, ' ')}"
        d = self.as_dict()
        for k, v in d.items():
            if type(v) in IMMUTABLE_TYPES:
                k = k.capitalize()
                s += f"\n{k.rjust(width, ' ')} | {v}"
        s += "\n\n"
        return s

    def as_dict(self) -> dict:
        """Returns a dictionary representation of this instance.

        Recursively exports nested objects, converting enums to values, datetimes to ISO
        strings, and calling ``as_dict()`` on objects that provide it.

        Returns:
            Dictionary with all fields serialized to primitives.
        """
        return {k: self._export_config(v) for k, v in self.__dict__.items()}

    @classmethod
    def _export_config(cls, v):  # pragma: no cover
        """Recursively converts values into storage-safe primitives.

        Args:
            v: Value to export.

        Returns:
            Exported value with enums, datetimes, and objects converted to primitives.
        """
        if isinstance(v, IMMUTABLE_TYPES):
            return v
        elif isinstance(v, SEQUENCE_TYPES):
            return type(v)(map(cls._export_config, v))
        elif isinstance(v, datetime):
            return v.isoformat()
        elif isinstance(v, Enum):
            return v.value
        elif isinstance(v, dict):
            return v
        elif hasattr(v, "as_dict"):
            return v.as_dict()
        else:
            return v


# ------------------------------------------------------------------------------------------------ #
#                                        PERSISTABLE                                               #
# ------------------------------------------------------------------------------------------------ #
@dataclass(kw_only=True)
class Entity(DataClass):
    """Base class for entity objects.

    Subclasses must implement the `namespace` and `key` properties for storage, and a `create`
    factory method for instantiation from a dictionary. The `value` property provides a dictionary
    representation of the object for storage, which can be overridden to include additional
    computed fields. The `embedding_text` property is used for generating text representations
    of the object for embedding in vector stores.

    Attributes:
        id: Unique identifier for this object.
        stage: Pipeline stage this object belongs to.
        entity_type: EntityType type of this object.
        created: Timestamp when this object was created.
        modified: Timestamp of the most recent update, or None.
        agent_name: Name of the agent that created this object, or None.

    Examples:
        >>> from sciven.domain.source import Source, SourceType
        >>> entity = Source(
        ...     name="arXiv",
        ...     description="Research paper source",
        ...     url="https://arxiv.org",
        ...     source_type=SourceType.PAPER,
        ...     tier=1,
        ...     agent_name="system",
        ... )
        >>> entity.entity_type.value
        'source'
    """

    id: str = field(default_factory=lambda: str(uuid7()))
    stage: Stage
    entity_type: EntityType
    entity_name: EntityName
    agent_name: str
    created: datetime = field(default_factory=datetime.now)
    modified: datetime | None = None

    # -------------------------------------------------------------------------------------------- #
    @property
    def namespace(self) -> tuple[str, ...]:
        """Namespace for this object, used for storage and retrieval."""
        return (self.stage.value, self.entity_type.value)

    # -------------------------------------------------------------------------------------------- #
    @property
    def key(self) -> str:
        """Unique key for this object."""
        return self.id

    # -------------------------------------------------------------------------------------------- #
    @property
    def value(self) -> dict[str, Any]:
        """Returns the serialized entity payload.

        Returns:
            Dictionary representation of this entity instance.
        """
        data = self.as_dict()
        data["embedding_text"] = self.embedding_text
        return data

    # -------------------------------------------------------------------------------------------- #
    @property
    def index(self) -> list[str] | None:
        """List of value fields to use for indexing and search."""
        return ["embedding_text"]

    # -------------------------------------------------------------------------------------------- #
    @property
    @abstractmethod
    def embedding_text(self) -> str:
        """Text used for embedding this object in vector stores."""
        pass

    # -------------------------------------------------------------------------------------------- #
    @classmethod
    @abstractmethod
    def create(cls, data: dict) -> Entity:
        """Factory method to create an instance from a dictionary.

        Args:
            data: Serialized object payload.

        Returns:
            A ``Entity`` subclass instance.
        """
        pass


# ------------------------------------------------------------------------------------------------ #
#                                         ENUM CLASS                                               #
# ------------------------------------------------------------------------------------------------ #
class EnumClass(Enum):
    """Base enum with shared helpers for Sciven enumerations.

    Provides a shared ``from_value`` factory so every signal enum can be
    constructed from its stored string value.

    Examples:
        >>> Stage.from_value("discovery")
        <Stage.DISCOVERY: 'discovery'>
    """

    @classmethod
    def from_value(cls, value: str):
        """Create an enum member from its string value.

        Args:
            value: The string value to match against enum members.

        Returns:
            The matching enum member.

        Raises:
            ValueError: If no member has the given value.
        """
        for member in cls:
            if member.value == value:
                return member
        raise ValueError(f"Invalid value '{value}' for enum {cls.__name__}")


# ------------------------------------------------------------------------------------------------ #
#                                   COMMON ENUMERATIONS                                            #
# ------------------------------------------------------------------------------------------------ #


class Segment(EnumClass):
    """Enumerates target customer segments.

    Attributes:
        ENTERPRISE: Large organizations and enterprises.
        CONSUMER: Individual end users.
        PROSUMER: Power users between consumer and enterprise profiles.

    Examples:
        >>> segment = Segment.ENTERPRISE
        >>> segment.value
        'enterprise'
        >>> Segment.from_value('consumer')
        <Segment.CONSUMER: 'consumer'>
    """

    ENTERPRISE = "enterprise"
    CONSUMER = "consumer"
    PROSUMER = "prosumer"


class Horizontal(EnumClass):
    """Enumerates cross-industry business functions.

    Attributes:
        SALES_MARKETING: Sales and marketing function.
        SERVICE: Customer service and support function.
        STRATEGY: Corporate or business strategy function.
        PRODUCT_SERVICE_DEVELOPMENT: Product and service development function.
        FINANCE: Finance and accounting function.
        ENGINEERING: Engineering and technical delivery function.
        OPERATIONS: Operations and process-execution function.

    Examples:
        >>> func = Horizontal.ENGINEERING
        >>> func.value
        'engineering'
        >>> Horizontal.from_value('sales_marketing')
        <Horizontal.SALES_MARKETING: 'sales_marketing'>
    """

    SALES_MARKETING = "sales_marketing"
    SERVICE = "service"
    STRATEGY = "strategy"
    PRODUCT_SERVICE_DEVELOPMENT = "product_service_development"
    FINANCE = "finance"
    ENGINEERING = "engineering"
    OPERATIONS = "operations"


# ------------------------------------------------------------------------------------------------ #
class Vertical(EnumClass):
    """Enumerates industry vertical classifications.

    Attributes:
        HEALTHCARE: Healthcare providers and related services.
        FINANCIAL_SERVICES: Banking, insurance, and financial institutions.
        MEDIA_COMMS: Media, entertainment, and communications.
        RETAIL: Retail commerce and distribution.
        CONSUMER_PRODUCTS: Consumer packaged and durable goods.
        LIFE_SCIENCES: Biotech, pharma, and life sciences.
        PROFESSIONAL_SERVICES: Consulting and other professional services.
        MANUFACTURING: Industrial and discrete manufacturing.
        EDUCATION: Education institutions and learning services.
        ENERGY: Energy production and utilities.
        TRANSPORTATION: Transportation and logistics services.
        AGRICULTURE: Agriculture and agri-business.
        REAL_ESTATE: Real estate and property services.
        OTHER: Industry not represented by predefined verticals.

    Examples:
        >>> vertical = Vertical.HEALTHCARE
        >>> vertical.value
        'healthcare'
        >>> Vertical.from_value('technology')
        Traceback (most recent call last):
            ...
        ValueError: Invalid value 'technology' for enum Vertical
    """

    HEALTHCARE = "healthcare"
    FINANCIAL_SERVICES = "financial_services"
    MEDIA_COMMS = "media_comms"
    RETAIL = "retail"
    CONSUMER_PRODUCTS = "consumer_products"
    LIFE_SCIENCES = "life_sciences"
    PROFESSIONAL_SERVICES = "professional_services"
    MANUFACTURING = "manufacturing"
    EDUCATION = "education"
    ENERGY = "energy"
    TRANSPORTATION = "transportation"
    AGRICULTURE = "agriculture"
    REAL_ESTATE = "real_estate"
    OTHER = "other"


# ------------------------------------------------------------------------------------------------ #
class ConsumerMarket(EnumClass):
    """Enumerates consumer market categories.

    Attributes:
        LIFESTYLE: Lifestyle-related products and services.
        HEALTH_AND_FITNESS: Health and fitness-related products and services.
        PRODUCTIVITY: Productivity-related products and services.
        ENTERTAINMENT: Entertainment-related products and services.
        EDUCATION: Education-related products and services.
        SOCIAL: Social media and communication products and services.
        FINANCE: Personal finance and fintech products and services.
        UTILITY: Utility and tool products and services.
        TRAVEL: Travel and transportation-related products and services.
        FOOD_AND_BEVERAGE: Food and beverage-related products and services.
        HOME: Home and living-related products and services.

    Examples:
        >>> market = ConsumerMarket.PRODUCTIVITY
        >>> market.value
        'productivity'
    """

    LIFESTYLE = "lifestyle"
    HEALTH_AND_FITNESS = "health_and_fitness"
    PRODUCTIVITY = "productivity"
    ENTERTAINMENT = "entertainment"
    EDUCATION = "education"
    SOCIAL = "social"
    FINANCE = "finance"
    UTILITY = "utility"
    TRAVEL = "travel"
    FOOD_AND_BEVERAGE = "food_and_beverage"
    HOME = "home"


# ------------------------------------------------------------------------------------------------ #
class ProsumerMarket(EnumClass):
    """Enumerates prosumer market categories.

    Attributes:
        DEVELOPER_TOOLS: Tools and platforms for software developers.
        CREATIVE_TOOLS: Tools for creative professionals and hobbyists.
        ENERGY: Energy production and management tools for prosumers.
        MAKER_TOOLS: Tools for makers, DIYers, and hardware tinkerers.
        GAMING: Gaming-related products and services.
        CONTENT_CREATION: Content creation and influencer tools and platforms.
        EDUCATION_AND_RESEARCH: Advanced educational and research tools and platforms.
        SPECIALIZED_PROFESSIONAL: Specialized tools for professions like design, engineering,
            data science, etc.
        SHARING_ECONOMY: Platforms enabling peer-to-peer sharing and monetization of assets
            and skills.

    Examples:
        >>> market = ProsumerMarket.DEVELOPER_TOOLS
        >>> market.value
        'developer_tools'
    """

    DEVELOPER_TOOLS = "developer_tools"
    CREATIVE_TOOLS = "creative_tools"
    ENERGY = "energy"
    MAKER_TOOLS = "maker_tools"
    GAMING = "gaming"
    CONTENT_CREATION = "content_creation"
    EDUCATION_AND_RESEARCH = "education_and_research"
    SPECIALIZED_PROFESSIONAL = "specialized_professional"
    SHARING_ECONOMY = "sharing_economy"


# ------------------------------------------------------------------------------------------------ #
class SignalAmplifier(EnumClass):
    """Enumerates factors that increase a signal's relevance or urgency.

    Attributes:
        VENTURE_CAPITAL: Capital allocation and investor activity that amplify momentum.
        ADOPTION: Observable uptake by users, buyers, or organizations.
        BEHAVIORAL: Sustained behavior changes that reinforce downstream impact.

    Examples:
        >>> amplifier = SignalAmplifier.VENTURE_CAPITAL
        >>> amplifier.value
        'venture_capital'
    """

    VENTURE_CAPITAL = "venture_capital"
    ADOPTION = "adoption"
    BEHAVIORAL = "behavioral"


# ------------------------------------------------------------------------------------------------ #
class EntityName(EnumClass):
    """Enumerates types of entities in the Sciven research platform.

    Attributes:
        SOURCE: A data source such as a journal or repository.
        ARXIV_SEARCH: Search metadata record for an arXiv query.
        PATENT: A patent document.
        NEWS: A news article.
        BLOG: A blog post or editorial article.
        REPORT: An industry or institutional report.
        PAPER: An academic or technical paper.
        INNOVATION_SIGNAL: An innovation signal derived from research.
        ACQUISITION_SIGNAL: An acquisition signal derived from research.
        MARKET_SIGNAL: A market signal derived from research.
        REFLECTION: A reflective analysis or critique of a signal or document.
        RUN: An execution run of a pipeline or agent workflow.

    Examples:
        >>> name = EntityName.PAPER
        >>> name.value
        'paper'
    """

    SOURCE = "source"
    # Search Entity Names
    ARXIV_SEARCH = "arxiv_search"

    # Document Entity Names
    PATENT = "patent"
    NEWS = "news"
    BLOG = "blog"
    REPORT = "report"
    PAPER = "paper"

    # Signal Entity Names
    INNOVATION_SIGNAL = "innovation_signal"
    ACQUISITION_SIGNAL = "acquisition_signal"
    MARKET_SIGNAL = "market_signal"

    # Reflection Entity Names
    REFLECTION = "reflection"
    DISCOVER_REFLECTION = "discover_reflection"
    DEVELOP_REFLECTION = "develop_reflection"
    DEFEND_REFLECTION = "defend_reflection"
    SIMULATE_REFLECTION = "simulate_reflection"
    BMODEL_REFLECTION = "bmodel_reflection"

    # Run Entity Name
    RUN = "run"


# ------------------------------------------------------------------------------------------------ #
class EntityType(EnumClass):
    """Enumerates types of entities in the Sciven research platform.

    Attributes:
         SEARCH: A search query or search result set.
         SOURCE: A data source such as a journal or repository.
         DOCUMENT: A document such as a paper, report, news article, or patent.
         SIGNAL: An innovation, acquisition, or market signal derived from research.
         REFLECTION: A reflective analysis or critique of a signal or document.
         RUN: An execution run of a pipeline or agent workflow.

    Examples:
        >>> entity_type = EntityType.SIGNAL
        >>> entity_type.value
        'signal'
    """

    SEARCH = "search"
    SOURCE = "source"
    DOCUMENT = "document"
    SIGNAL = "signal"
    REFLECTION = "reflection"
    RUN = "run"


# ------------------------------------------------------------------------------------------------ #
class EvidenceType(EnumClass):
    """Enumerates document and signal evidence types.

    Attributes:
        INNOVATION: Category for innovation-related documents and signals.
        MARKET: Category for market-related documents and signals.
        ACQUISITION: Category for acquisition-related documents and signals.
    """

    INNOVATION = "innovation"
    MARKET = "market"
    ACQUISITION = "acquisition"


# ------------------------------------------------------------------------------------------------ #
class TaskType(EnumClass):
    """Enumerates common tasks types performed in the Sciven research pipeline.

    Attributes:
        CURATE_DOCUMENTS: Task of curating signal-bearing documents.
        DETECT_SIGNALS: Task of detecting innovation signals from curated documents.
        VALIDATE_SIGNALS: Task of validating detected signals.
    """

    CURATE_DOCUMENTS = "curate_documents"
    DETECT_SIGNALS = "detect_signals"
    VALIDATE_SIGNALS = "validate_signals"


# ------------------------------------------------------------------------------------------------ #
class DiscontinuityCategory(EnumClass):
    """Enumerates categories of discontinuity claims for innovation signals.

    Attributes:
        COST_COLLAPSE: Dramatic reduction in cost that changes competitive dynamics.
        CAPABILITY_FRONTIER: Breakthrough capability that was previously unattainable.
        ACCESSIBILITY_SHIFT: Technology or service becoming broadly accessible to new audiences.
        RELIABILITY_THRESHOLD: Reliability reaching a level that enables new use cases.
        PERFORMANCE_JUMP: Step-change improvement in measurable performance metrics.

    Examples:
        >>> category = DiscontinuityCategory.CAPABILITY_FRONTIER
        >>> category.value
        'capability_frontier'
    """

    COST_COLLAPSE = "cost_collapse"
    CAPABILITY_FRONTIER = "capability_frontier"
    ACCESSIBILITY_SHIFT = "accessibility_shift"
    RELIABILITY_THRESHOLD = "reliability_threshold"
    PERFORMANCE_JUMP = "performance_jump"


# ------------------------------------------------------------------------------------------------ #
class Stage(EnumClass):
    """Enumerates stages of the Sciven research pipeline.

    Attributes:
        DISCOVERY: Stage for signal discovery.
        DEVELOPMENT: Stage for hypothesis development.
        VALIDATION: Stage for market research, experimentation, simulation and validation.
        STRATEGY: Stage for business modeling and GTM strategy.
    """

    DISCOVERY = "discovery"
    DEVELOPMENT = "development"
    VALIDATION = "validation"
    STRATEGY = "strategy"


# ------------------------------------------------------------------------------------------------ #
class SourceID(EnumClass):
    """Enumeration of data sources identifiers for document retrieval.

    Attributes:
        ARXIV: arXiv academic paper repository.

    Examples:
        >>> source = SourceID.ARXIV
        >>> source.value
        'arxiv'
    """

    ARXIV = "arxiv"
