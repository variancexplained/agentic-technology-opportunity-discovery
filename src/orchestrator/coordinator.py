from __future__ import annotations

import asyncio
from typing import Any

from src.agents.base import BaseAgent


class Coordinator:
    """Runs one or more agents and collects their results.

    This is the only place that calls multiple agents. Agents do not
    call each other directly.
    """

    def __init__(self, agents: list[BaseAgent]) -> None:
        self.agents = agents

    async def run_parallel(self, input: Any) -> list[Any]:
        """Run all agents concurrently with the same input."""
        return await asyncio.gather(*(agent.run(input) for agent in self.agents))

    async def run_pipeline(self, input: Any) -> Any:
        """Run agents sequentially, passing each result to the next."""
        result = input
        for agent in self.agents:
            result = await agent.run(result)
        return result
