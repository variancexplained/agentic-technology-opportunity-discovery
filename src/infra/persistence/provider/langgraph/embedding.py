#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Sciven                                                                              #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /sciven/adapters                                                                    #
# Filename   : embedding.py                                                                        #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/sciven-centre/sciven                                             #
# ------------------------------------------------------------------------------------------------ #
# Created    : Tuesday April 14th 2026 03:59:25 am                                                 #
# Modified   : Thursday June 4th 2026 12:27:33 am                                                  #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #
"""Embedding Module for Langgraph."""

from collections.abc import Callable
from dataclasses import dataclass

from sentence_transformers import SentenceTransformer

# ================================================================================================ #
model = None


def get_model() -> SentenceTransformer:
    """Lazily loads the SentenceTransformer model."""
    global model
    if model is None:
        model = SentenceTransformer("all-mpnet-base-v2", device="cpu")
    return model


# ================================================================================================ #
def embedding_fn(text: str) -> list[float]:
    """Embedding function using SentenceTransformer."""
    encoder = get_model()
    return encoder.encode(text, show_progress_bar=False).tolist()


# ================================================================================================ #
#                                    EMBEDDING CONFIG                                              #
# ================================================================================================ #
@dataclass
class EmbeddingConfig:
    """Bundles an embedding function with its output dimensions.

    Args:
        fn: Callable that takes a string and returns a list of floats.
        dims: Number of dimensions produced by the embedding function.
    """

    fn: Callable[[str], list[float]] = embedding_fn
    dims: int = 768
