#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/services                                                                    #
# Filename   : __init__.py                                                                         #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Tuesday April 7th 2026 04:01:51 am                                                  #
# Modified   : Saturday June 27th 2026 06:34:04 am                                                 #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
"""Sciven services module."""

import os

from dotenv import load_dotenv

from sciven.infra.persistence.provider.langgraph.embedding import EmbeddingConfig

load_dotenv()

# ------------------------------------------------------------------------------------------------ #
#                                 SERVICE CONFIGURATION                                            #
# ------------------------------------------------------------------------------------------------ #
DATABASE_URI = os.environ["DATABASE_URI"]
EMBEDDING_CONFIG = None


# ------------------------------------------------------------------------------------------------ #
def set_embedding_config() -> None:
    """Lazily initialize the embedding configuration."""
    embedding_config = globals().get("EMBEDDING_CONFIG")
    if embedding_config is None:
        embedding_config = EmbeddingConfig()
        globals()["EMBEDDING_CONFIG"] = embedding_config
