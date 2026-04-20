from typing import Dict, Callable, Any
from .protocol import Task
import asyncio

class Router:
    def __init__(self):
        self.agents: Dict[str, Callable[[Task], Any]] = {}

    def register_agent(self, agent_id: str, handler: Callable[[Task], Any]):
        self.agents[agent_id] = handler

    async def send_task(self, task: Task) -> Any:
        if task.receiver in self.agents:
            return await self.agents[task.receiver](task)
        else:
            raise ValueError(f"Agent {task.receiver} not registered")

router = Router()