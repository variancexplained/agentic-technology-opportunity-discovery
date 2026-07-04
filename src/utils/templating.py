#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Description: Sciven: The Science of Venture Development                                          #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/utils                                                                       #
# Filename   : templating.py                                                                       #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Wednesday July 1st 2026 01:31:40 am                                                 #
# Modified   : Wednesday July 1st 2026 01:33:23 am                                                 #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
import re
from typing import Any

# ------------------------------------------------------------------------------------------------ #
# Matches ``${NAME}`` placeholders only (bare ``$NAME`` and literal ``$`` are left untouched).
_PLACEHOLDER = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


# ------------------------------------------------------------------------------------------------ #
#                                       MODULE HELPERS                                             #
# ------------------------------------------------------------------------------------------------ #
def fill_template(template: str, values: dict[str, Any]) -> str:
    """Substitutes ``${NAME}`` placeholders in ``template`` with values from ``values``.

    Only ``${NAME}`` tokens are considered; a placeholder whose name is absent from ``values``
    is left verbatim, which lets substitution run in two passes (construction time then
    activation time) without failing on values that are not yet known.

    Args:
        template: The source text containing ``${NAME}`` placeholders.
        values: Mapping of placeholder name to replacement value.

    Returns:
        The text with every known placeholder replaced; unknown placeholders are preserved.
    """

    def _replace(match: re.Match) -> str:
        key = match.group(1)
        return str(values[key]) if key in values else match.group(0)

    return _PLACEHOLDER.sub(_replace, template)
