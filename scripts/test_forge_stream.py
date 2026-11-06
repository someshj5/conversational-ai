import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from agent_api.views import get_forge_agent

"""To run this file from root dir
# PYTHONPATH=. uv run python scripts/test_forge_stream.py
"""


def main():
    agent = get_forge_agent()

    messages = [
        {
            "role": "user",
            "content": (
                "Explain what create_agent does in this repository. "
                "Keep the answer concise."
            ),
        }
    ]

    print("\n--- STREAM STARTED ---\n")

    for message_chunk, metadata in agent.stream(
        {"messages": messages},
        stream_mode="messages",
    ):
        # Inspect only assistant model output.
        if metadata.get("langgraph_node") != "model":
            continue

        content = getattr(message_chunk, "content", "")

        if isinstance(content, str) and content:
            print(content, end="", flush=True)

    print("\n\n--- STREAM COMPLETED ---")


if __name__ == "__main__":
    main()