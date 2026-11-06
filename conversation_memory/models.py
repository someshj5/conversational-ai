
import uuid

from django.db import models


class Conversation(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    thread_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
    )
    title = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.title or str(self.id)


class ConversationMessage(models.Model):
    class Role(models.TextChoices):
        SYSTEM = "system", "System"
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        TOOL = "tool", "Tool"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sequence = models.PositiveIntegerField()
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
    )
    content = models.TextField(blank=True, default="")
    tool_name = models.CharField(max_length=255, blank=True, default="")
    tool_call_id = models.CharField(max_length=255, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "sequence"],
                name="unique_conversation_message_sequence",
            ),
        ]
        indexes = [
            models.Index(
                fields=["conversation", "role"],
                name="conv_msg_role_idx",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.conversation_id}:"
            f"{self.sequence} ({self.role})"
        )


class ConversationSummary(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="summaries",
    )
    version = models.PositiveIntegerField()
    covers_sequence_from = models.PositiveIntegerField()
    covers_sequence_to = models.PositiveIntegerField()
    summary_text = models.TextField()
    source_messages = models.ManyToManyField(
        ConversationMessage,
        related_name="summaries",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "version"],
                name="unique_conversation_summary_version",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Summary v{self.version} "
            f"for conversation {self.conversation_id}"
        )

