#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Description: Sciven: The Science of Venture Development                                          #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/utils                                                                       #
# Filename   : log.py                                                                              #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Saturday June 13th 2026                                                            #
# Modified   : Wednesday June 24th 2026 08:10:45 pm                                                #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
"""Logging configuration for Sciven.

Configures the ``sciven`` package logger with a single file handler that writes
one JSON object per line. Call :func:`config_logger` at any entry point; modules
then log normally via ``logging.getLogger(__name__)``.

Structured fields are supplied per call, not baked into the config, since not
every event is entity-scoped. Pass any extra fields via the standard ``extra``
kwarg and they appear as top-level JSON keys::

    logger.info("Persisted document", extra={"stage": "discovery", "agent_name": agent})

Events with no entity context simply omit ``extra``.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import MutableMapping
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any

# ------------------------------------------------------------------------------------------------ #
PACKAGE_LOGGER = "sciven"

#: Standard ``LogRecord`` attributes, used to detect caller-supplied ``extra`` fields.
_RESERVED = frozenset(vars(logging.makeLogRecord({}))) | {"message", "asctime"}


# ------------------------------------------------------------------------------------------------ #
#                                       JSON FORMATTER                                             #
# ------------------------------------------------------------------------------------------------ #
class JsonFormatter(logging.Formatter):
    """Renders each log record as a single line of JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialize a record to a JSON line.

        Any fields the caller passed via ``extra`` (e.g. ``stage``,
        ``entity_type``, ``agent_name``) are merged in as top-level keys.

        Args:
            record: The log record to format.

        Returns:
            A JSON string with timestamp, level, logger, and message; caller
            ``extra`` fields and an ``exception`` field are added when present.
        """
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created).astimezone().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


# ------------------------------------------------------------------------------------------------ #
#                                    FIELD LOGGER ADAPTER                                          #
# ------------------------------------------------------------------------------------------------ #
class FieldLoggerAdapter(logging.LoggerAdapter):
    """A logger that stamps a fixed set of fields onto every record.

    The bound fields are merged into each call's ``extra`` so entity-scoped
    callers need not repeat identity fields. A per-call ``extra`` takes
    precedence on key conflicts, so an individual call can add or override.

    Construct one with :meth:`create` rather than the constructor.
    """

    def process(
        self, msg: Any, kwargs: MutableMapping[str, Any]
    ) -> tuple[Any, MutableMapping[str, Any]]:
        """Merge the bound fields beneath any per-call ``extra``.

        Args:
            msg: The log message.
            kwargs: Keyword arguments for the logging call.

        Returns:
            The message and kwargs with ``extra`` set to the merged fields.
        """
        kwargs["extra"] = {**(self.extra or {}), **kwargs.get("extra", {})}
        return msg, kwargs

    @classmethod
    def create(
        cls, logger: logging.Logger | logging.LoggerAdapter, **fields: object
    ) -> FieldLoggerAdapter:
        """Return a logger that stamps ``fields`` onto every record.

        Call once at a run or entity boundary to keep entity-scoped logging DRY:
        bind the identity fields, then log normally. Passing an existing adapter
        merges the new fields on top of its bound ones, so context can be layered
        (e.g. run-level, then entity-level).

        Args:
            logger: A base logger, or an existing adapter whose fields to extend.
            **fields: Fields to stamp onto every record (e.g. ``stage``, ``agent_name``).

        Returns:
            A ``FieldLoggerAdapter`` carrying the merged fields.
        """
        # Lazily configure the package logger on first use, since there is no single
        # entry point. Guarded so an explicit config_logger(...) call is not overridden.
        if not logging.getLogger(PACKAGE_LOGGER).handlers:
            config_logger()
        if isinstance(logger, logging.LoggerAdapter):
            merged = dict(logger.extra) if logger.extra else {}
            merged.update(fields)
            return cls(logger.logger, merged)
        return cls(logger, dict(fields))


# ------------------------------------------------------------------------------------------------ #
#                                       CONFIG LOGGER                                              #
# ------------------------------------------------------------------------------------------------ #
def config_logger(
    level: int | str = logging.INFO,
    *,
    log_dir: str | os.PathLike[str] = "./logs",
    filename: str = "sciven.log",
    interval: int = 1,
    when: str = "midnight",
    backup_count: int = 5,
) -> logging.Logger:
    """Configure the ``sciven`` logger to write JSON lines to a rotating file.

    Idempotent: repeated calls with the same file do not stack handlers, so it is
    safe to call from multiple entry points. Logs are not propagated to the root
    logger, so the file is the only sink.

    Args:
        level: Minimum level to record (int or level name, e.g. ``"DEBUG"``).
        log_dir: Directory for the log file; created if it does not exist.
        filename: Name of the log file within ``log_dir``.
        when: Rotation interval type (e.g. ``"midnight"``, ``"H"``, ``"D"``).
        interval: Rotation interval count (e.g. ``1`` for every midnight, ``2`` for every 2 hours).
        backup_count: Number of rotated files to retain.

    Returns:
        The configured ``sciven`` package logger.
    """
    directory = Path(log_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = os.path.abspath(directory / filename)

    logger = logging.getLogger(PACKAGE_LOGGER)
    logger.setLevel(level)
    logger.propagate = False

    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler) and handler.baseFilename == path:
            return logger

    handler = TimedRotatingFileHandler(
        path,
        when=when,
        interval=interval,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    return logger
