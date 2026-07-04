#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Description: The Science of Venture Development                                                  #
# Version    : 0.1.1                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/utils                                                                       #
# Filename   : formatting.py                                                                       #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Saturday May 2nd 2026 12:15:52 am                                                   #
# Modified   : Sunday May 31st 2026 11:20:23 pm                                                    #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
"""Utility functions for formatting and normalizing data."""

import re
from types import SimpleNamespace
from urllib.parse import urlparse, urlunparse


# ------------------------------------------------------------------------------------------------ #
def normalize_url(url: str) -> str:
    """Normalizes a URL and removes common tracking query parameters."""
    TRACKING_PARAMS = {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "ref",
        "source",
    }
    parsed = urlparse(url.strip().lower())
    # Strip tracking query params
    if parsed.query:
        clean_query = "&".join(
            p for p in parsed.query.split("&") if p.split("=")[0] not in TRACKING_PARAMS
        )
    else:
        clean_query = ""
    # Strip trailing slash from path
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((parsed.scheme, parsed.netloc, path, "", clean_query, ""))


# ------------------------------------------------------------------------------------------------ #
def to_kebab(text: str) -> str:
    """Converts a string to kebab-case safe for use as a filename."""
    cleaned = re.sub(r'[<>:"/\\|?*\s]+', "-", text.strip().lower())
    return re.sub(r"-+", "-", cleaned).strip("-")


# ------------------------------------------------------------------------------------------------ #
def dict_to_namespace(data):
    """Recursively converts a dictionary to a SimpleNamespace, allowing attribute access to keys."""
    if isinstance(data, dict):
        # Recursively convert inner dictionaries
        return SimpleNamespace(**{k: dict_to_namespace(v) for k, v in data.items()})
    elif isinstance(data, list):
        # Elements inside a list might also contain dictionaries
        return [dict_to_namespace(item) for item in data]
    else:
        return data
