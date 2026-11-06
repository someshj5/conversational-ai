
from typing import Any, Sequence

from langchain.agents.middleware import AgentMiddleware
from langchain_core.runnables import RunnableConfig


class PinSkillsMiddleware(AgentMiddleware):
    """Set the skills to inject before the agent's model call."""

    def __init__(self, pinned_skills: Sequence[str]) -> None:
        self.pinned_skills = list(pinned_skills)

    def before_agent(
        self,
        state: dict[str, Any],
        runtime: Any,
    ) -> dict[str, Any] | None:
        if not self.pinned_skills:
            return None

        return {"pinned_skills": self.pinned_skills}
