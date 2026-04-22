from typing import Dict, Callable, Any
from .protocol import Task
import asyncio

class Router:

    #Takes a Task and returns any result.
    def __init__(self):
        self.agents: Dict[str, Callable[[Task], Any]] = {}

    # Connect the agent to the router 
    def register_agent(self, agent_id: str, handler: Callable[[Task], Any]):
        self.agents[agent_id] = handler

    # send task
    async def send_task(self, task: Task) -> Any:
        if task.receiver in self.agents:
            return await self.agents[task.receiver](task)
        else:
            raise ValueError(f"Agent {task.receiver} not registered")

router = Router()