
from datetime import datetime
from uuid import UUID

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework.exceptions import APIException # type: ignore

from taskapp.models import Todo, TodoCreationRequest
from taskapp.service import TodoService
from user_management.service import TenantService, UserService
from django.utils import timezone
from django.db import transaction
from rest_framework.exceptions import NotFound # type: ignore

class TodoApprovalService:
    """Prepare and manage approved Todo creation requests."""

    @staticmethod
    def _parse_datetime(value: str | None, field: str) -> datetime | None:
        if value is None:
            return None

        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            raise ValueError(f"{field} must be an ISO-8601 datetime.")

        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError(f"{field} must include a timezone offset.")

        return parsed

    @staticmethod
    @transaction.atomic
    def prepare(
        *,
        tenant_id: UUID,
        created_by_id: UUID,
        title: str,
        description: str = "",
        start_time: str | None = None,
        end_time: str | None = None,
        status: str = Todo.Status.PENDING,
    ) -> TodoCreationRequest:
        """Validate and persist a pending request without creating a Todo."""

        if not title or not title.strip():
            raise ValueError("title cannot be empty.")

        title = title.strip()
        if len(title) > 255:
            raise ValueError("title cannot exceed 255 characters.")

        if status not in Todo.Status.values:
            raise ValueError(f"Unsupported Todo status: {status!r}.")

        start = TodoApprovalService._parse_datetime(start_time, "start_time")
        end = TodoApprovalService._parse_datetime(end_time, "end_time")

        if start and end and end <= start:
            raise ValueError("end_time must be after start_time.")

        tenant = TenantService.get_tenant(tenant_id)
        UserService.get_user(
            tenant_id=tenant_id,
            user_id=created_by_id,
        )

        TodoService._validate_within_business_hours(
            tenant=tenant,
            start_time=start,
            end_time=end,
        )

        candidate = Todo(
            tenant=tenant,
            created_by_id=created_by_id,
            title=title,
            description=description,
            start_time=start,
            end_time=end,
            status=status,
        )
        candidate.full_clean()

        payload = {
            "title": title,
            "description": description,
            "start_time": start.isoformat() if start else None,
            "end_time": end.isoformat() if end else None,
            "status": status,
        }

        return TodoCreationRequest.objects.create(
            tenant=tenant,
            created_by_id=created_by_id,
            payload=payload,
            state=TodoCreationRequest.State.PENDING,
        )


    @staticmethod
    @transaction.atomic
    def approve(
        *,
        request_id: UUID,
        tenant_id: UUID,
        created_by_id: UUID,
    ) -> TodoCreationRequest:
        """Approve a pending request for the authorized tenant and creator."""

        request = (
            TodoCreationRequest.objects.select_for_update()
            .filter(
                id=request_id,
                tenant_id=tenant_id,
                created_by_id=created_by_id,
            )
            .first()
        )

        if request is None:
            raise NotFound("Todo creation request not found.")

        if request.state != TodoCreationRequest.State.PENDING:
            raise ValueError(
                f"Cannot approve a request in state {request.state!r}."
            )

        request.state = TodoCreationRequest.State.APPROVED
        request.approved_at = timezone.now()
        request.save(update_fields=["state", "approved_at"])

        return request

    @staticmethod
    @transaction.atomic
    def execute(
        *,
        request_id: UUID,
        tenant_id: UUID,
        created_by_id: UUID,
    ) -> Todo:
        """Execute an approved request exactly once."""

        request = (
            TodoCreationRequest.objects.select_for_update()
            .filter(
                id=request_id,
                tenant_id=tenant_id,
                created_by_id=created_by_id,
            )
            .first()
        )

        if request is None:
            raise NotFound("Todo creation request not found.")

        if request.state != TodoCreationRequest.State.APPROVED:
            raise ValueError(
                "Only approved, unused requests can be executed."
            )

        payload = request.payload

        # Revalidate the persisted snapshot at execution time.
        start = TodoApprovalService._parse_datetime(
            payload["start_time"], "start_time"
        )
        end = TodoApprovalService._parse_datetime(
            payload["end_time"], "end_time"
        )

        todo = TodoService.create_todo(
            tenant_id=tenant_id,
            created_by_id=created_by_id,
            title=payload["title"],
            description=payload["description"],
            start_time=start,
            end_time=end,
            status=payload["status"],
        )

        request.state = TodoCreationRequest.State.CONSUMED
        request.consumed_at = timezone.now()
        request.save(update_fields=["state", "consumed_at"])

        return todo
