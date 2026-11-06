from collections.abc import Sequence
from typing import Any


def invoke_with_skills(
    agent: Any,
    input_state: dict[str, Any],
    pinned_skills: Sequence[str] | None = None,
    **kwargs: Any,
) -> Any:
    """Invoke an agent with explicitly selected skills."""
    state = dict(input_state)

    if pinned_skills:
        state["pinned_skills"] = list(pinned_skills)

    return agent.invoke(state, **kwargs)
