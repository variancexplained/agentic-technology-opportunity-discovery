#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Description: Sciven: The Science of Venture Development                                          #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/utils                                                                       #
# Filename   : pdf.py                                                                              #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Sunday May 31st 2026 11:45:26 pm                                                    #
# Modified   : Monday June 1st 2026 12:00:08 am                                                    #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
"""PDF acquisition and section-aware text extraction for the Sciven pipeline.

``ResearchPDF`` wraps a single PDF document and exposes the surface an agent
needs to triage and mine a paper:

* ``download``  : fetch a PDF from a URL to a local path.
* ``list_sections`` : enumerate the section headings the paper actually has.
* ``get_section``   : return the text of one named section, with explicit
  not-found handling so callers (agents or pipeline code) never receive a
  silent empty string they cannot distinguish from a genuinely empty section.
* ``full_text`` : the whole document as Markdown, as an escape hatch.

Section discovery is driven by the Markdown that ``pymupdf4llm`` emits, but
heading detection is heuristic: numbered headings reliably become Markdown
headings (``## 1. Introduction``) while unnumbered ones (``Abstract``) may
arrive as plain lines. The parser therefore augments Markdown headings with a
small vocabulary of canonical paper headings so common unnumbered sections are
still discoverable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import httpx
import pymupdf
import pymupdf4llm

# ------------------------------------------------------------------------------------------------ #
# Canonical headings that frequently appear unnumbered and may not be promoted
# to Markdown headings by the extractor. Matched case-insensitively against a
# line that stands alone. This is recall-oriented on purpose: a false heading
# is cheap (an agent ignores it); a missed heading hides claim-bearing text.
PLAIN_HEADING_VOCAB: frozenset[str] = frozenset(
    {
        "abstract",
        "introduction",
        "background",
        "related work",
        "methods",
        "methodology",
        "materials and methods",
        "approach",
        "experiments",
        "experimental setup",
        "evaluation",
        "results",
        "results and discussion",
        "discussion",
        "findings",
        "limitations",
        "conclusion",
        "conclusions",
        "future work",
        "references",
        "acknowledgments",
        "acknowledgements",
        "appendix",
    }
)

# A Markdown ATX heading line, e.g. "## 3. Results". Captures the heading text.
MARKDOWN_HEADING_RE = re.compile(r"^(#{1,6})\s+(?P<text>.+?)\s*#*\s*$")

# Markdown fenced code block delimiters. Heading detection is suspended inside a fenced
# block so a commented "# ..." line in extracted code is not mistaken for a heading.
CODE_FENCE_PREFIXES = ("```", "~~~")

# PDF magic bytes. The PDF spec allows the "%PDF-" header to appear anywhere within the
# first 1024 bytes (some files prepend a byte-order mark or whitespace), so the download
# scans that window rather than requiring the bytes at offset 0.
PDF_MAGIC = b"%PDF-"
PDF_HEADER_WINDOW = 1024


class SectionNotFoundError(LookupError):
    """Raised when a requested section heading is not present in the document.

    Carries the list of available headings so the caller (or an agent) can
    recover by choosing a heading that exists rather than guessing again.

    Args:
        requested: The heading string that was requested.
        available: The headings actually present in the document.

    Attributes:
        requested: The heading string that was requested.
        available: The headings actually present in the document.
    """

    def __init__(self, requested: str, available: list[str]) -> None:
        self.requested = requested
        self.available = available
        super().__init__(f"Section {requested!r} not found. Available sections: {available}")


class PDFDownloadError(RuntimeError):
    """Raised when a URL could not be downloaded as a PDF.

    Args:
        url: The URL that was requested.
        reason: Human-readable description of the failure.

    Attributes:
        url: The URL that was requested.
        reason: Human-readable description of the failure.
    """

    def __init__(self, url: str, reason: str) -> None:
        self.url = url
        self.reason = reason
        super().__init__(f"Failed to download PDF from {url!r}: {reason}")


@dataclass
class Section:
    """A single resolved section of a document.

    Attributes:
        heading: The heading text as it appears in the document.
        body: The text belonging to the section, up to the next heading.
        level: Heading depth (1 for top level). Plain-vocab headings use 1.
    """

    heading: str
    body: str
    level: int = 1


@dataclass(kw_only=True)
class ResearchPDF:
    """Wraps one PDF for download and section-aware extraction.

    A ``ResearchPDF`` is bound to a single local PDF file. Instantiate it with a
    path to an existing file, or use the :meth:`download` classmethod to fetch
    one first. Markdown conversion is performed lazily on first access and
    cached; section parsing derives from that cached Markdown.

    The underlying ``pymupdf.Document`` is opened lazily and should be released
    with :meth:`close` (or by using the instance as a context manager).

    Attributes:
        path: Local filesystem path to the PDF.
    """

    path: Path

    doc: pymupdf.Document | None = field(default=None, init=False, repr=False)
    markdown: str | None = field(default=None, init=False, repr=False)
    sections: list[Section] | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        """Normalises ``path`` to a ``Path`` and verifies the file exists."""
        self.path = Path(self.path)
        if not self.path.is_file():
            raise FileNotFoundError(f"No PDF at {self.path}")

    # -- acquisition ------------------------------------------------------

    @classmethod
    def download(
        cls,
        url: str,
        filepath: str | Path,
        *,
        allowed_hosts: frozenset[str] | None = None,
        timeout: float = 30.0,
        max_bytes: int = 50 * 1024 * 1024,
        max_redirects: int = 5,
    ) -> ResearchPDF:
        """Downloads a PDF from ``url`` to ``filepath`` and returns a wrapper.

        The download is validated: the response must succeed, must not exceed
        ``max_bytes``, and the ``%PDF-`` header must appear near the start of the
        payload so a 404 HTML page or an error body is never silently written as a
        ``.pdf``. Redirects are followed manually so the scheme and host allowlist is
        enforced on every hop, not only the original URL.

        Args:
            url: HTTP(S) URL of the PDF.
            filepath: Local destination path. Parent directories are created.
            allowed_hosts: If given, the request host must be in this set, e.g.
                ``frozenset({"arxiv.org", "export.arxiv.org"})``, and the constraint is
                enforced on every redirect hop. Use this when the URL originates from
                search results rather than your code.
            timeout: Per-request timeout in seconds.
            max_bytes: Reject downloads larger than this many bytes.
            max_redirects: Maximum number of redirects to follow. Each hop's scheme and
                host are validated before it is requested.

        Returns:
            A ``ResearchPDF`` bound to the downloaded file.

        Raises:
            PDFDownloadError: On a non-PDF scheme or disallowed host (including a redirect
                target), an HTTP error, too many redirects, an oversize payload, or a body
                that is not a PDF.
        """
        def validate_target(target: str) -> None:
            """Validates a request target's scheme and host against the allowlist."""
            parsed = urlparse(target)
            if parsed.scheme not in ("http", "https"):
                raise PDFDownloadError(url, f"unsupported scheme {parsed.scheme!r}")
            if allowed_hosts is not None and parsed.hostname not in allowed_hosts:
                raise PDFDownloadError(url, f"host {parsed.hostname!r} not allowed")

        validate_target(url)

        destination = Path(filepath)
        destination.parent.mkdir(parents=True, exist_ok=True)

        # Follow redirects manually so the allowlist is enforced on every hop. Automatic
        # redirects would let a URL on an allowed host bounce the download to any other host.
        payload = b""
        target = url
        try:
            with httpx.Client(timeout=timeout, follow_redirects=False) as client:
                for _ in range(max_redirects + 1):
                    with client.stream("GET", target) as response:
                        if response.is_redirect:
                            location = response.headers.get("location")
                            if not location:
                                raise PDFDownloadError(url, "redirect without a Location header")
                            target = str(response.url.join(location))
                            validate_target(target)
                            continue
                        response.raise_for_status()
                        chunks: list[bytes] = []
                        total = 0
                        for chunk in response.iter_bytes():
                            total += len(chunk)
                            if total > max_bytes:
                                raise PDFDownloadError(url, f"exceeds max_bytes ({max_bytes})")
                            chunks.append(chunk)
                        payload = b"".join(chunks)
                        break
                else:
                    raise PDFDownloadError(url, f"too many redirects (> {max_redirects})")
        except httpx.HTTPError as exc:
            raise PDFDownloadError(url, str(exc)) from exc

        if PDF_MAGIC not in payload[:PDF_HEADER_WINDOW]:
            raise PDFDownloadError(url, "response body is not a PDF")

        destination.write_bytes(payload)
        return cls(path=destination)

    # -- lifecycle --------------------------------------------------------

    def open(self) -> pymupdf.Document:
        """Opens (once) and returns the underlying ``pymupdf.Document``."""
        if self.doc is None:
            self.doc = pymupdf.open(self.path)
        return self.doc

    def close(self) -> None:
        """Releases the underlying document handle."""
        if self.doc is not None:
            self.doc.close()
            self.doc = None

    def __enter__(self) -> ResearchPDF:
        """Opens the document and returns this wrapper for context-manager use.

        Returns:
            This ``ResearchPDF`` instance.
        """
        self.open()
        return self

    def __exit__(self, *exc: object) -> None:
        """Closes the document when leaving a context-manager block."""
        self.close()

    # -- extraction -------------------------------------------------------

    def full_text(self) -> str:
        """Returns the entire document as Markdown (cached after first call)."""
        if self.markdown is None:
            markdown = pymupdf4llm.to_markdown(self.open(), show_progress=False)
            if not isinstance(markdown, str):
                raise RuntimeError("pymupdf4llm.to_markdown did not return a string")
            self.markdown = markdown
        return self.markdown

    def list_sections(self) -> list[str]:
        """Returns the heading text of every section detected in the document.

        Order matches document order. Headings come from Markdown ATX headings
        plus standalone lines matching the canonical paper-heading vocabulary.
        """
        return [section.heading for section in self._parse_sections()]

    def get_section(self, heading: str) -> str:
        """Returns the body text of the section with the given heading.

        Matching is case-insensitive and ignores surrounding whitespace and
        trailing punctuation, but is otherwise exact: the caller is expected to
        pass a heading obtained from :meth:`list_sections`.

        Args:
            heading: The section heading to retrieve.

        Returns:
            The section body text.

        Raises:
            SectionNotFoundError: If no section matches ``heading``. The error
                carries the available headings so the caller can recover.
        """
        target = self._normalise(heading)
        for section in self._parse_sections():
            if self._normalise(section.heading) == target:
                return section.body
        raise SectionNotFoundError(heading, self.list_sections())

    # -- internal ---------------------------------------------------------

    @staticmethod
    def _normalise(heading: str) -> str:
        """Lowercases and strips whitespace, leading numbering, and trailing punctuation."""
        text = heading.strip().lower()
        text = re.sub(r"^[\d.\s]+", "", text)  # drop leading "3. " / "3.1 "
        text = text.rstrip(".:")
        return text.strip()

    def _parse_sections(self) -> list[Section]:
        """Parses the cached Markdown into ordered sections (cached)."""
        if self.sections is not None:
            return self.sections

        lines = self.full_text().splitlines()
        boundaries: list[tuple[int, str, int]] = []  # (line_index, heading, level)

        in_code_block = False
        for index, raw in enumerate(lines):
            line = raw.strip()
            # Toggle on fenced code blocks; '#' lines inside code are not headings.
            if line.startswith(CODE_FENCE_PREFIXES):
                in_code_block = not in_code_block
                continue
            if in_code_block or not line:
                continue
            match = MARKDOWN_HEADING_RE.match(line)
            if match:
                boundaries.append((index, match.group("text").strip(), len(match.group(1))))
                continue
            # Standalone line matching a canonical heading, even without '#'.
            if self._normalise(line) in PLAIN_HEADING_VOCAB:
                boundaries.append((index, line, 1))

        sections: list[Section] = []
        for position, (line_index, heading, level) in enumerate(boundaries):
            start = line_index + 1
            end = boundaries[position + 1][0] if position + 1 < len(boundaries) else len(lines)
            body = "\n".join(lines[start:end]).strip()
            sections.append(Section(heading=heading, body=body, level=level))

        self.sections = sections
        return sections
