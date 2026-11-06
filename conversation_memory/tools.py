
import os

import django
from langchain.tools import tool

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from conversation_memory.services import (
    retrieve_conversation as retrieve_messages,
    search_conversation as search_messages,
)


@tool
def search_conversation(conversation_id: str, query: str) -> str:
    """Search summaries and original messages in a conversation.

    Use this when historical conversation context may contain
    information needed to answer the current question.
    """
    result = search_messages(conversation_id, query)

    import json
    return json.dumps(result, default=str, ensure_ascii=False)


@tool
def retrieve_conversation(
    conversation_id: str,
    summary_id: str = "",
    message_ids: list[str] | None = None,
    after_sequence: int = 0,
    limit: int = 100,
) -> str:
    """Retrieve original conversation messages.

    Use summary_id to retrieve messages covered by a summary,
    message_ids to retrieve specific messages, or after_sequence
    and limit to retrieve an ordered segment of history.
    """
    import json

    result = retrieve_messages(
        conversation_id=conversation_id,
        summary_id=summary_id or None,
        message_ids=message_ids,
        after_sequence=after_sequence,
        limit=limit,
    )

    return json.dumps(
        [
            {
                "message_id": str(message.id),
                "sequence": message.sequence,
                "role": message.role,
                "content": message.content,
                "tool_name": message.tool_name,
                "tool_call_id": message.tool_call_id,
                "metadata": message.metadata,
            }
            for message in result
        ],
        ensure_ascii=False,
    )


from langchain.tools import tool


def make_conversation_tools(conversation_id: str):
    """Create tools scoped to one application-selected conversation."""

    @tool
    def search_current_conversation(query: str) -> str:
        """Search summaries and original messages in the current conversation.
        Use this to find relevant information from earlier interactions.
        """
        import json

        result = search_messages(
            conversation_id=conversation_id,
            query=query,
        )
        return json.dumps(result, default=str, ensure_ascii=False)

    @tool
    def retrieve_current_conversation(
        summary_id: str = "",
        message_ids: list[str] | None = None,
        after_sequence: int = 0,
        limit: int = 100,
    ) -> str:
        """Retrieve original messages from the current conversation.
        Use summary_id to retrieve messages covered by a summary,
        message_ids to retrieve specific messages, or after_sequence
        and limit to retrieve an ordered segment of history.
        """
        import json

        result = retrieve_messages(
            conversation_id=conversation_id,
            summary_id=summary_id or None,
            message_ids=message_ids,
            after_sequence=after_sequence,
            limit=limit,
        )

        return json.dumps(
            [
                {
                    "message_id": str(message.id),
                    "sequence": message.sequence,
                    "role": message.role,
                    "content": message.content,
                    "tool_name": message.tool_name,
                    "tool_call_id": message.tool_call_id,
                    "metadata": message.metadata,
                }
                for message in result
            ],
            default=str,
            ensure_ascii=False,
        )

    return [
        search_current_conversation,
        retrieve_current_conversation,
    ]

