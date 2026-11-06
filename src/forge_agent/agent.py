
import logging
import os

from pathlib import Path
from typing import Any, Sequence

from dotenv import load_dotenv
from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

logger = logging.getLogger(__name__)

from src.forge_agent.backends import create_backend
from src.forge_agent.permissions import AGENT_PERMISSIONS
from src.forge_agent.tools import create_search_code_tool

# SKILL_SOURCES = ["/skills/"]

model = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=os.environ["OPENAI_API_KEY"],
    temperature=0,
)

logger.info("LLM initialized | provider=openai | model=gpt-4.1-mini")


SYSTEM_PROMPT = """
You are Forge, a repository-aware coding assistant.

Your responsibility is to answer questions about the source code
in the configured repository.

Supported tasks:
1. Locate features, classes, functions, methods and API endpoints.
2. Explain how existing code works.
3. Trace execution flows across modules.
4. Identify relevant files and line numbers.
5. Explain dependencies and relationships between components.

TOOL USAGE RULES:

1. Use search_code to locate indexed symbols.
2. Use grep for literal text searches across repository files.
3. Use glob and ls to explore repository structure.
4. Use read_file to inspect actual source code.
5. Inspect implementations before making claims about behavior.
6. Never invent files, functions, implementations or line numbers.
7. If source code is unavailable, explicitly state that.

RESTRICTIONS:

- Never access application databases.
- Never create, update or delete database records.
- Never modify repository files.
- Never execute application code or shell commands.

Always distinguish verified source-code findings from inference.
Include file paths and line numbers whenever possible.
"""





def create_agent(
    *,
    repository_root: Path,
    index_dir: Path,
    middleware: Sequence[Any] | None = None,
):
    logger.info("Creating Forge repository assistant")

    agent = create_deep_agent(
        model=model,
        tools=[create_search_code_tool(index_dir)],
        backend=create_backend(repository_root),
        permissions=AGENT_PERMISSIONS,
        name="forge-repository-assistant",
        system_prompt=SYSTEM_PROMPT,
        middleware=list(middleware or []),
    )

    logger.info("Forge repository assistant initialized")
    return agent