#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Description: Sciven: The Science of Venture Development                                          #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/utils                                                                       #
# Filename   : markdown.py                                                                         #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Wednesday July 1st 2026 01:34:59 am                                                 #
# Modified   : Wednesday July 1st 2026 01:40:28 am                                                 #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
from pathlib import Path

# ------------------------------------------------------------------------------------------------ #


def read_markdown(filepath: str) -> str:
    """Reads a markdown file and returns its content.

    Args:
        filepath: The path to the markdown file.

    Returns:
        The content of the markdown file as a string.
    """
    path = Path(filepath)
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    return path.read_text(encoding="utf-8")


# ------------------------------------------------------------------------------------------------ #
def write_markdown(filepath: str, content: str) -> None:
    """Writes content to a markdown file.

    Args:
        filepath: The path to the markdown file.
        content: The markdown content to write.
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
