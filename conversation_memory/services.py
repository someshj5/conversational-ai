
from django.db import transaction
from django.db.models import Max
from uuid import UUID
from conversation_memory.models import Conversation, ConversationMessage


def create_conversation(
    thread_id: str,
    title: str = "",
) -> Conversation:
    conversation, _ = Conversation.objects.get_or_create(
        thread_id=thread_id,
        defaults={"title": title},
    )
    return conversation


@transaction.atomic
def append_message(
    conversation_id,
    role: str,
    content: str = "",
    *,
    tool_name: str = "",
    tool_call_id: str = "",
    metadata: dict | None = None,
) -> ConversationMessage:
    conversation = Conversation.objects.select_for_update().get(
        pk=conversation_id
    )

    last_sequence = (
        ConversationMessage.objects
        .filter(conversation=conversation)
        .aggregate(max_sequence=Max("sequence"))["max_sequence"]
    )

    sequence = (last_sequence or 0) + 1

    message = ConversationMessage.objects.create(
        conversation=conversation,
        sequence=sequence,
        role=role,
        content=content,
        tool_name=tool_name,
        tool_call_id=tool_call_id,
        metadata=metadata or {},
    )

    return message


def get_message(message_id) -> ConversationMessage:
    return ConversationMessage.objects.get(pk=message_id)


def get_conversation_messages(
    conversation_id,
    *,
    after_sequence: int = 0,
    limit: int = 100,
) -> list[ConversationMessage]:
    if limit < 1 or limit > 500:
        raise ValueError("limit must be between 1 and 500")

    return list(
        ConversationMessage.objects
        .filter(
            conversation_id=conversation_id,
            sequence__gt=after_sequence,
        )
        .order_by("sequence")[:limit]
    )


from conversation_memory.models import (
    Conversation,
    ConversationMessage,
    ConversationSummary,
)


@transaction.atomic
def create_summary(
    conversation_id,
    summary_text: str,
    covers_sequence_from: int,
    covers_sequence_to: int,
) -> ConversationSummary:
    if covers_sequence_from < 1:
        raise ValueError("covers_sequence_from must be >= 1")

    if covers_sequence_to < covers_sequence_from:
        raise ValueError(
            "covers_sequence_to must be >= covers_sequence_from"
        )

    conversation = Conversation.objects.get(pk=conversation_id)

    source_messages = list(
        ConversationMessage.objects.filter(
            conversation=conversation,
            sequence__gte=covers_sequence_from,
            sequence__lte=covers_sequence_to,
        ).order_by("sequence")
    )

    expected_count = covers_sequence_to - covers_sequence_from + 1

    if len(source_messages) != expected_count:
        raise ValueError(
            "The requested sequence range contains missing messages."
        )

    latest_version = (
        ConversationSummary.objects
        .filter(conversation=conversation)
        .aggregate(max_version=Max("version"))["max_version"]
        or 0
    )

    summary = ConversationSummary.objects.create(
        conversation=conversation,
        version=latest_version + 1,
        covers_sequence_from=covers_sequence_from,
        covers_sequence_to=covers_sequence_to,
        summary_text=summary_text,
    )

    summary.source_messages.set(source_messages)
    return summary


def get_summary(summary_id) -> ConversationSummary:
    return ConversationSummary.objects.prefetch_related(
        "source_messages"
    ).get(pk=summary_id)


def retrieve_conversation(
    *,
    conversation_id,
    summary_id=None,
    message_ids=None,
    after_sequence=None,
    limit=100,
) -> list[ConversationMessage]:
    
    conversation_id = UUID(str(conversation_id))

    if summary_id is not None:
        summary_id = UUID(str(summary_id))

    if summary_id is not None:
        summary = get_summary(summary_id)

        if summary.conversation_id != conversation_id:
            raise ValueError(
                "Summary does not belong to the requested conversation."
            )

        return list(
            summary.source_messages.order_by("sequence")
        )

    if message_ids is not None:
        return list(
            ConversationMessage.objects.filter(
                conversation_id=conversation_id,
                id__in=message_ids,
            ).order_by("sequence")
        )

    return get_conversation_messages(
        conversation_id,
        after_sequence=after_sequence or 0,
        limit=limit,
    )


from django.db.models import Q


def search_conversation(
    conversation_id,
    query: str,
    limit: int = 10,
) -> dict:
    if not query.strip():
        raise ValueError("query must not be empty")

    if limit < 1 or limit > 50:
        raise ValueError("limit must be between 1 and 50")

    terms = query.casefold().split()

    summaries = ConversationSummary.objects.filter(
        conversation_id=conversation_id,
    )

    for term in terms:
        summaries = summaries.filter(summary_text__icontains=term)

    messages = ConversationMessage.objects.filter(
        conversation_id=conversation_id,
    )

    message_query = Q()
    for term in terms:
        message_query |= Q(content__icontains=term)

    messages = messages.filter(message_query).order_by("-sequence")[:limit]

    return {
        "summaries": list(
            summaries.order_by("-version")[:limit].values(
                "id",
                "version",
                "covers_sequence_from",
                "covers_sequence_to",
                "summary_text",
            )
        ),
        "messages": list(
            messages.values(
                "id",
                "sequence",
                "role",
                "content",
                "tool_name",
                "tool_call_id",
            )
        ),
    }

