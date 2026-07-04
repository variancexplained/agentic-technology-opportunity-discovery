#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Description: Sciven: The Science of Venture Development                                          #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/utils                                                                       #
# Filename   : config.py                                                                           #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Tuesday June 9th 2026 10:18:12 pm                                                   #
# Modified   : Wednesday June 24th 2026 06:12:51 pm                                                #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
"""Configuration loading utilities for the Sciven pipeline."""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import yaml
from dotenv import load_dotenv

load_dotenv()

# Project-root config.yaml, used when neither an explicit path nor SCIVEN_CONFIG is set.
_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.yaml"


# ------------------------------------------------------------------------------------------------ #
class ConfigReader:
    """Reads a YAML config file into a dot-referenceable object.

    The parsed mapping is converted to a ``SimpleNamespace`` so values are accessed by attribute
    (``config.min_queries``) rather than by key. Nested mappings are converted recursively, and
    mappings inside lists are converted too, so an arbitrarily nested config is dot-referenceable
    throughout.

    Example:
        >>> config = ConfigReader().read("discovery", "curate_documents")
        >>> config.min_queries
        3
    """

    def __init__(self, path: str | Path | None = None) -> None:
        """Initialize the reader for a config file.

        Args:
            path: Path to the YAML config file. When ``None``, the path is resolved from
                the ``CONFIG_FILEPATH`` environment variable, falling back to the project-root
                ``config.yaml``.
        """
        if path is None:
            path = os.getenv("CONFIG_FILEPATH", str(_DEFAULT_CONFIG_PATH))
        self._path = Path(path)

    def read(self, *keys: str) -> SimpleNamespace:
        """Read the config file and return its contents as a namespace.

        Args:
            *keys: Optional sequence of nested keys to drill into, applied in order. Each key
                selects a sub-section, e.g. ``read("discovery", "curate_documents")``. With no
                keys, the entire file is returned.

        Returns:
            SimpleNamespace: The selected config mapping with values exposed as attributes.

        Raises:
            FileNotFoundError: If the config file does not exist.
            ValueError: If the file's top-level YAML value is not a mapping.
        """
        if not self._path.is_file():
            raise FileNotFoundError(f"Config file not found: {self._path}")

        with self._path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file)

        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise ValueError(
                f"Config file must contain a top-level mapping, got {type(data).__name__}: "
                f"{self._path}"
            )
        for key in keys:
            data = data.get(key, {})
        return cast(SimpleNamespace, ConfigReader._to_namespace(data))

    # -------------------------------------------------------------------------------------------- #
    @staticmethod
    def _to_namespace(value: object) -> object:
        """Recursively convert mappings to namespaces, descending into lists.

        Args:
            value: A parsed YAML value (mapping, sequence, or scalar).

        Returns:
            The value with every mapping converted to a ``SimpleNamespace``.
        """
        if isinstance(value, dict):
            return SimpleNamespace(
                **{key: ConfigReader._to_namespace(val) for key, val in value.items()}
            )
        if isinstance(value, list):
            return [ConfigReader._to_namespace(item) for item in value]
        return value
