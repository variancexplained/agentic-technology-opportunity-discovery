#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Description: Sciven: The Science of Venture Development                                          #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/utils                                                                       #
# Filename   : io.py                                                                               #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Tuesday June 9th 2026 10:18:12 pm                                                   #
# Modified   : Sunday June 14th 2026 01:06:25 am                                                   #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
"""Configuration loading utilities for the Sciven pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import yaml


# ------------------------------------------------------------------------------------------------ #
def read_json(path: Path, to_namespace: bool = True) -> SimpleNamespace | dict:
    """Read the config file and return its contents as a namespace.

    Args:
        path: Path to the config file to read.
        to_namespace: Whether to convert the dictionary to a SimpleNamespace.

    Returns:
        SimpleNamespace | dict: The config mapping with values exposed as attributes if
        `to_namespace` is True, otherwise a dictionary.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If the file's top-level YAML value is not a mapping.
    """
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError(
            f"File must contain a top-level mapping, got {type(data).__name__}: {path}"
        )
    if to_namespace:
        return cast(SimpleNamespace, _to_namespace(data))
    return data


# ------------------------------------------------------------------------------------------------ #
def write_json(path: Path, data: SimpleNamespace | dict, *, indent: int = 2) -> None:
    """Write a mapping to a JSON file, creating parent directories as needed.

    Args:
        path: Destination path for the JSON file.
        data: The mapping to write, as a dict or SimpleNamespace.
        indent: Indentation level for the serialized JSON. Defaults to 2.

    Raises:
        TypeError: If `data` is not a dict or SimpleNamespace.
    """
    if isinstance(data, SimpleNamespace):
        data = _to_dict(data)
    if not isinstance(data, dict):
        raise TypeError(f"data must be a dict or SimpleNamespace, got {type(data).__name__}")

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=indent, default=str)


# -------------------------------------------------------------------------------------------- #
def _to_namespace(value: object) -> object:
    """Recursively convert mappings to namespaces and lists of namespaces."""
    if isinstance(value, dict):
        return SimpleNamespace(**{key: _to_namespace(val) for key, val in value.items()})
    if isinstance(value, list):
        return [_to_namespace(item) for item in value]
    return value


# -------------------------------------------------------------------------------------------- #
def _to_dict(value: object) -> object:
    """Recursively convert namespaces back to mappings, descending into lists.

    Args:
        value: A value that may contain SimpleNamespace nodes.

    Returns:
        The value with every SimpleNamespace converted to a dict.
    """
    if isinstance(value, SimpleNamespace):
        return {key: _to_dict(val) for key, val in vars(value).items()}
    if isinstance(value, list):
        return [_to_dict(item) for item in value]
    return value
