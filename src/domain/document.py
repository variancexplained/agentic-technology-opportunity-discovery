#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/types                                                                       #
# Filename   : document.py                                                                         #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Wednesday April 8th 2026 01:31:40 am                                                #
# Modified   : Saturday June 27th 2026 05:00:47 am                                                 #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
"""Document data models used by the Sciven research pipeline."""

import contextlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from sciven.domain import (
    Entity,
    EntityName,
    EntityType,
    EnumClass,
    SourceID,
    Stage,
)
from sciven.domain.core import EvidenceType
from sciven.utils.formatting import normalize_url, to_kebab


# ------------------------------------------------------------------------------------------------ #
class DocumentStatus(EnumClass):
    """Enumerates the possible statuses of a document.

    Attributes:
        NEW: The document has been newly curated and has not yet been processed.
        PROCESSED: The document has been processed for Signals.

    Examples:
        >>> status = DocumentStatus.NEW
        >>> status.value
        'new'
        >>> DocumentStatus.from_value('processed')
        <DocumentStatus.PROCESSED: 'processed'>
    """

    NEW = "new"
    PROCESSED = "processed"


# ------------------------------------------------------------------------------------------------ #
class DocumentFormat(EnumClass):
    """Enumerates supported document formats.

    Attributes:
        PDF: Portable Document Format, typically used for papers and reports.
        HTML: HyperText Markup Language, used for web pages and blogs.
        MARKDOWN: Markdown format, used for lightweight documents and notes.

    Examples:
        >>> doc_format = DocumentFormat.PDF
        >>> doc_format.value
        'pdf'
        >>> DocumentFormat.from_value('markdown')
        <DocumentFormat.MARKDOWN: 'markdown'>
    """

    PDF = "pdf"
    HTML = "html"
    MARKDOWN = "markdown"


# ------------------------------------------------------------------------------------------------ #
#                                          DOCUMENT                                                #
# ------------------------------------------------------------------------------------------------ #
@dataclass(kw_only=True)
class Document(Entity, ABC):
    """Base class for a normalized document associated with a source.

    Holds only the fields common to every document type. Type-specific fields (abstract,
    publication venue, local file path, revision timestamp, and so on) are declared on the
    concrete subclasses. Identifier construction is subclass-specific and is not performed
    here; the ``id`` is taken as supplied (typically set by the provider mapper).

    Attributes:
        authors: Primary authors or credited agent_names.
        title: Document title.
        url: Canonical URL where the document can be accessed.
        entity_name: The EntityName of this document.
        document_format: The DocumentFormat of this document.
        name: Stable kebab-case slug derived from the title. Set once at construction and
            never changed thereafter; a FileManager uses it as the stored PDF filename
            (``[name].pdf``), so altering it would orphan the stored file.
        published: Optional publication timestamp.
        run_id: Identifier of the run that produced this document.
        search_id: Identifier of the search that found this document.
        source_id: Identifier of the parent source record.

    Examples:
        Instantiate a concrete subclass:

        >>> paper = ResearchPaper(
        ...     id='paper-1',
        ...     authors=['Ada Lovelace'],
        ...     title='Analytical Engine Notes',
        ...     url='https://example.org/paper',
        ...     document_format=DocumentFormat.PDF,
        ...     abstract='A short summary.',
        ...     run_id='run-1',
        ...     search_id='search-1',
        ...     source_id='source-1',
        ...     agent_name='system',
        ... )
        >>> paper.entity_name
        <EntityName.PAPER: 'paper'>
    """

    authors: list[str]
    title: str
    url: str
    document_format: DocumentFormat
    name: str | None = None
    published: datetime | str | None = None

    stage: Stage = Stage.DISCOVERY
    entity_type: EntityType = EntityType.DOCUMENT
    entity_name: EntityName = EntityName.PAPER
    evidence_type: EvidenceType

    # Lineage
    run_id: str
    search_id: str | None = None
    source_id: SourceID
    status: DocumentStatus = DocumentStatus.NEW

    def __post_init__(self) -> None:
        """Normalizes the URL, parses the published timestamp, and sets the name once."""
        if self.url:
            self.url = normalize_url(self.url)
        if isinstance(self.published, str):
            with contextlib.suppress(ValueError):
                self.published = datetime.fromisoformat(self.published)
        if self.name is None:
            self.name = to_kebab(self.title)

    @property
    @abstractmethod
    def embedding_text(self) -> str:
        """Text used for embedding this document in vector stores."""
        ...

    @classmethod
    @abstractmethod
    def create(cls, data: dict) -> Document:
        """Hydrates a document instance from a serialized dict.

        Concrete subclasses must override this and must not call ``super``.

        Args:
            data: A dictionary containing the document fields.

        Returns:
            A hydrated Document subclass instance.
        """
        subclass = ENTITY_NAME_MAP[EntityName.from_value(data["entity_name"])]
        return subclass.create(data)


# ------------------------------------------------------------------------------------------------ #
#                                       RESEARCH PAPER                                             #
# ------------------------------------------------------------------------------------------------ #
@dataclass(kw_only=True)
class ResearchPaper(Document):
    """An academic or technical paper.

    Attributes:
        abstract: Summary text used for retrieval and embedding.
        updated: Optional revision timestamp (arXiv's ``updated`` field).

    Examples:
        >>> paper = ResearchPaper(
        ...     id='paper-1',
        ...     authors=['Ada Lovelace'],
        ...     title='Analytical Engine Notes',
        ...     url='https://example.org/paper',
        ...     document_format=DocumentFormat.PDF,
        ...     abstract='A short summary.',
        ...     run_id='run-1',
        ...     search_id='search-1',
        ...     source_id='source-1',
        ...     agent_name='system',
        ... )
        >>> paper.title
        'Analytical Engine Notes'
    """

    abstract: str
    updated: datetime | str | None = None
    entity_name: EntityName = EntityName.PAPER
    evidence_type: EvidenceType = EvidenceType.INNOVATION

    def __post_init__(self) -> None:
        """Normalizes URL, published, and updated after initialization."""
        super().__post_init__()
        if isinstance(self.updated, str):
            with contextlib.suppress(ValueError):
                self.updated = datetime.fromisoformat(self.updated)

    @property
    def embedding_text(self) -> str:
        """Returns the title and abstract joined for embedding generation."""
        return f"{self.title} {self.abstract}"

    @classmethod
    def create(cls, data: dict) -> ResearchPaper:
        """Hydrates a ResearchPaper from a serialized dict.

        Args:
            data: A dictionary containing the paper fields.

        Returns:
            A hydrated ResearchPaper instance.
        """
        return cls(
            id=data["id"],
            authors=data["authors"],
            title=data["title"],
            url=data["url"],
            name=data.get("name"),
            abstract=data["abstract"],
            updated=data.get("updated"),
            document_format=DocumentFormat.from_value(data["document_format"]),
            published=data.get("published"),
            run_id=data["run_id"],
            search_id=data["search_id"],
            source_id=SourceID.from_value(data["source_id"]),
            entity_name=EntityName.from_value(data["entity_name"]),
            evidence_type=EvidenceType.from_value(data.get("evidence_type")),
            status=DocumentStatus.from_value(data.get("status", DocumentStatus.NEW.value)),
            created=datetime.fromisoformat(data["created"]),
            modified=datetime.fromisoformat(data["modified"]) if data.get("modified") else None,
            agent_name=data["agent_name"],
        )


# ------------------------------------------------------------------------------------------------ #
#                                           REPORT                                                 #
# ------------------------------------------------------------------------------------------------ #
@dataclass(kw_only=True)
class Report(Document):
    """An industry or institutional report.

    Attributes:
        abstract: Summary text used for retrieval and embedding.
        publication: Publishing venue or outlet.

    Examples:
        >>> report = Report(
        ...     id='report-1',
        ...     authors=['Research Team'],
        ...     title='State of AI',
        ...     url='https://example.org/report',
        ...     document_format=DocumentFormat.PDF,
        ...     abstract='Annual synthesis.',
        ...     publication='Sciven Insights',
        ...     run_id='run-1',
        ...     search_id='search-1',
        ...     source_id='source-1',
        ...     agent_name='system',
        ... )
        >>> report.publication
        'Sciven Insights'
    """

    abstract: str
    publication: str
    entity_name: EntityName = EntityName.REPORT

    @property
    def embedding_text(self) -> str:
        """Returns the title and abstract joined for embedding generation."""
        return f"{self.title} {self.abstract}"

    @classmethod
    def create(cls, data: dict) -> Report:
        """Hydrates a Report from a serialized dict.

        Args:
            data: A dictionary containing the report fields.

        Returns:
            A hydrated Report instance.
        """
        return cls(
            id=data["id"],
            authors=data["authors"],
            title=data["title"],
            url=data["url"],
            name=data.get("name"),
            abstract=data["abstract"],
            publication=data["publication"],
            document_format=DocumentFormat.from_value(data["document_format"]),
            published=data.get("published"),
            run_id=data["run_id"],
            search_id=data["search_id"],
            source_id=SourceID.from_value(data["source_id"]),
            entity_name=EntityName.from_value(data["entity_name"]),
            evidence_type=EvidenceType.from_value(data.get("evidence_type")),
            status=DocumentStatus.from_value(data.get("status", DocumentStatus.NEW.value)),
            created=datetime.fromisoformat(data["created"]),
            modified=datetime.fromisoformat(data["modified"]) if data.get("modified") else None,
            agent_name=data["agent_name"],
        )


# ------------------------------------------------------------------------------------------------ #
#                                            BLOG                                                  #
# ------------------------------------------------------------------------------------------------ #
@dataclass(kw_only=True)
class Blog(Document):
    """A blog post or editorial article.

    Examples:
        >>> blog = Blog(
        ...     id='blog-1',
        ...     authors=['Editorial Desk'],
        ...     title='Why Open Models Matter',
        ...     url='https://example.org/blog',
        ...     document_format=DocumentFormat.HTML,
        ...     run_id='run-1',
        ...     search_id='search-1',
        ...     source_id='source-1',
        ...     agent_name='system',
        ... )
        >>> blog.entity_name
        <EntityName.BLOG: 'blog'>
    """

    entity_name: EntityName = EntityName.BLOG

    @property
    def embedding_text(self) -> str:
        """Returns the title for embedding generation."""
        return self.title

    @classmethod
    def create(cls, data: dict) -> Blog:
        """Hydrates a Blog from a serialized dict.

        Args:
            data: A dictionary containing the blog fields.

        Returns:
            A hydrated Blog instance.
        """
        return cls(
            id=data["id"],
            authors=data["authors"],
            title=data["title"],
            url=data["url"],
            name=data.get("name"),
            document_format=DocumentFormat.from_value(data["document_format"]),
            published=data.get("published"),
            run_id=data["run_id"],
            search_id=data["search_id"],
            source_id=SourceID.from_value(data["source_id"]),
            entity_name=EntityName.from_value(data["entity_name"]),
            evidence_type=EvidenceType.from_value(data.get("evidence_type")),
            created=datetime.fromisoformat(data["created"]),
            modified=datetime.fromisoformat(data["modified"]) if data.get("modified") else None,
            agent_name=data["agent_name"],
            status=DocumentStatus.from_value(data.get("status", DocumentStatus.NEW.value)),
        )


# ------------------------------------------------------------------------------------------------ #
#                                            NEWS                                                  #
# ------------------------------------------------------------------------------------------------ #
@dataclass(kw_only=True)
class News(Document):
    """A news article.

    Examples:
        >>> article = News(
        ...     id='news-1',
        ...     authors=['Newswire'],
        ...     title='Model Costs Decline',
        ...     url='https://example.org/news',
        ...     document_format=DocumentFormat.HTML,
        ...     run_id='run-1',
        ...     search_id='search-1',
        ...     source_id='source-1',
        ...     agent_name='system',
        ... )
        >>> article.entity_name
        <EntityName.NEWS: 'news'>
    """

    entity_name: EntityName = EntityName.NEWS

    @property
    def embedding_text(self) -> str:
        """Returns the title for embedding generation."""
        return self.title

    @classmethod
    def create(cls, data: dict) -> News:
        """Hydrates a News from a serialized dict.

        Args:
            data: A dictionary containing the news fields.

        Returns:
            A hydrated News instance.
        """
        return cls(
            id=data["id"],
            authors=data["authors"],
            title=data["title"],
            url=data["url"],
            name=data.get("name"),
            document_format=DocumentFormat.from_value(data["document_format"]),
            published=data.get("published"),
            run_id=data["run_id"],
            search_id=data["search_id"],
            source_id=SourceID.from_value(data["source_id"]),
            entity_name=EntityName.from_value(data["entity_name"]),
            evidence_type=EvidenceType.from_value(data.get("evidence_type")),
            created=datetime.fromisoformat(data["created"]),
            modified=datetime.fromisoformat(data["modified"]) if data.get("modified") else None,
            agent_name=data["agent_name"],
            status=DocumentStatus.from_value(data.get("status", DocumentStatus.NEW.value)),
        )


# ------------------------------------------------------------------------------------------------ #
#                                           PATENT                                                 #
# ------------------------------------------------------------------------------------------------ #
@dataclass(kw_only=True)
class Patent(Document):
    """A patent filing or publication.

    The ``id`` is the patent identifier supplied by the source; it is not derived.

    Examples:
        >>> patent = Patent(
        ...     id='patent-1',
        ...     authors=['Inventor'],
        ...     title='Adaptive Sparse Inference',
        ...     url='https://example.org/patent',
        ...     document_format=DocumentFormat.HTML,
        ...     run_id='run-1',
        ...     search_id='search-1',
        ...     source_id='source-1',
        ...     agent_name='system',
        ... )
        >>> patent.entity_name
        <EntityName.PATENT: 'patent'>
    """

    entity_name: EntityName = EntityName.PATENT

    @property
    def embedding_text(self) -> str:
        """Returns the title for embedding generation.

        Note:
            Provisional. Patent sources may expose an abstract or summary; revisit the
            embedding text once a patent source is integrated.
        """
        return self.title

    @classmethod
    def create(cls, data: dict) -> Patent:
        """Hydrates a Patent from a serialized dict.

        Args:
            data: A dictionary containing the patent fields.

        Returns:
            A hydrated Patent instance.
        """
        return cls(
            id=data["id"],
            authors=data["authors"],
            title=data["title"],
            url=data["url"],
            name=data.get("name"),
            document_format=DocumentFormat.from_value(data["document_format"]),
            published=data.get("published"),
            run_id=data["run_id"],
            search_id=data["search_id"],
            source_id=SourceID.from_value(data["source_id"]),
            entity_name=EntityName.from_value(data["entity_name"]),
            evidence_type=EvidenceType.from_value(data.get("evidence_type")),
            created=datetime.fromisoformat(data["created"]),
            modified=datetime.fromisoformat(data["modified"]) if data.get("modified") else None,
            agent_name=data["agent_name"],
            status=DocumentStatus.from_value(data.get("status", DocumentStatus.NEW.value)),
        )


# ------------------------------------------------------------------------------------------------ #
#                                   DOCUMENT TYPE REGISTRY                                         #
# ------------------------------------------------------------------------------------------------ #
ENTITY_NAME_MAP: dict[EntityName, type[Document]] = {
    EntityName.PAPER: ResearchPaper,
    EntityName.REPORT: Report,
    EntityName.BLOG: Blog,
    EntityName.NEWS: News,
    EntityName.PATENT: Patent,
}
