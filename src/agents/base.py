from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """Minimal base class for all agents in this project.

    Subclasses must implement `run()`. The orchestrator calls `run()` directly
    and may call multiple agents concurrently via asyncio.gather().
    """

    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    async def run(self, input: Any) -> Any:
        """Execute the agent's task and return a result."""
        ...

    async def __call__(self, input: Any) -> Any:
        return await self.run(input)
