"""Base agent class for all NetOpsHub agents."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from netopshub.models import AgentMessage, AgentTask

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for NetOpsHub agents.

    Each agent specializes in a specific domain (discovery, diagnosis,
    compliance, etc.) and communicates through a standardized message
    and task interface.
    """

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self._task_history: list[AgentTask] = []
        self._message_history: list[AgentMessage] = []

    @abstractmethod
    async def process(self, task: AgentTask) -> AgentTask:
        """Process a task and return the result."""
        ...

    @abstractmethod
    async def chat(self, message: str, context: dict[str, Any] | None = None) -> str:
        """Handle a chat message and return a response."""
        ...

    def log_message(self, role: str, content: str) -> None:
        """Log a message to history."""
        msg = AgentMessage(
            role=role,
            content=content,
            agent_name=self.name,
        )
        self._message_history.append(msg)

    def get_history(self, limit: int = 50) -> list[AgentMessage]:
        """Get recent message history."""
        return self._message_history[-limit:]

    def get_task_history(self, limit: int = 50) -> list[AgentTask]:
        """Get recent task history."""
        return self._task_history[-limit:]

    def _complete_task(self, task: AgentTask, output: dict[str, Any]) -> AgentTask:
        """Mark a task as completed."""
        task.status = "completed"
        task.output_data = output
        task.completed_at = datetime.utcnow()
        self._task_history.append(task)
        return task

    def _fail_task(self, task: AgentTask, error: str) -> AgentTask:
        """Mark a task as failed."""
        task.status = "failed"
        task.error = error
        task.completed_at = datetime.utcnow()
        self._task_history.append(task)
        return task

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"
