import uuid
import zoneinfo
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from user_management.models import Tenant,User

def validate_timezone(value: str):
    """Validates that the provided timezone string is a valid IANA timezone."""
    if value not in zoneinfo.available_timezones():
        raise ValidationError(f"'{value}' is not a valid IANA timezone.")


class Todo(models.Model):
    """Todo model representing a task within a Tenant, with status tracking and business hours validation."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="todos",
        db_index=True,
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="created_todos",
        db_index=True,
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "todos"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "created_by"]),
            models.Index(fields=["tenant", "start_time"]),
        ]

    def clean(self):
        super().clean()
        # Ensure user belongs to the assigned tenant
        if self.created_by_id and self.tenant_id: # type: ignore
            if self.created_by.tenant_id != self.tenant_id: # type: ignore
                raise ValidationError("created_by user must belong to the specified tenant.")

        # Ensure start_time is before end_time if both are provided
        if self.start_time and self.end_time:
            if self.start_time > self.end_time:
                raise ValidationError("end_time must be greater than start_time.")

    def __str__(self):
        return f"[{self.status}] {self.title}"


class TodoCreationRequest(models.Model):
    """A prepared Todo request with a one-time approval lifecycle."""

    class State(models.TextChoices):
        PENDING = "PENDING", "Pending approval"
        APPROVED = "APPROVED", "Approved"
        CONSUMED = "CONSUMED", "Consumed"
        REJECTED = "REJECTED", "Rejected"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="todo_creation_requests",
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="todo_creation_requests",
    )

    # Immutable proposal snapshot used during execution.
    payload = models.JSONField()

    state = models.CharField(
        max_length=16,
        choices=State.choices,
        default=State.PENDING,
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "todo_creation_requests"
        indexes = [
            models.Index(fields=["tenant", "created_by", "state"]),
        ]

    def clean(self):
        super().clean()
        if (
            self.created_by_id # type: ignore
            and self.tenant_id # type: ignore
            and self.created_by.tenant_id != self.tenant_id # type: ignore
        ):
            raise ValidationError(
                "created_by user must belong to the specified tenant."
            )
        