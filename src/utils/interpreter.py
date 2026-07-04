#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Description: Sciven: The Science of Venture Development                                          #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/utils                                                                       #
# Filename   : interpreter.py                                                                      #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Wednesday July 1st 2026 01:42:39 am                                                 #
# Modified   : Wednesday July 1st 2026 01:46:32 am                                                 #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
"""Interpreter Utilities."""

import sys
from pathlib import Path


# ------------------------------------------------------------------------------------------------ #
def get_interpreter_prefix(filepath: str) -> list[str]:
    """Chooses the interpreter prefix for a script based on its file extension.

    Args:
        filepath: Path to the script file.

    Returns:
        The interpreter prefix for the run command: ``[sys.executable]`` for ``.py``, ``["bash"]``
        for ``.sh``/``.bash``, and ``[]`` for any other extension (executed directly).
    """
    suffix = Path(filepath).suffix
    if suffix == ".py":
        return [sys.executable]
    if suffix in (".sh", ".bash"):
        return ["bash"]
    return []
