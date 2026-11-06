import zoneinfo
from datetime import datetime
from typing import Optional
from uuid import UUID
from django.db.models import QuerySet
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import NotFound, ValidationError as DRFValidationError # type: ignore

from .models import Tenant, Todo
from .repository import TodoRepository
from user_management.service import *

def _handle_django_validation(func):
    """Decorator to convert Django's ValidationError into DRF's ValidationError."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except DjangoValidationError as exc:
            raise DRFValidationError(detail=exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
    return wrapper



class TodoService:
    """Business logic for managing Tenant-scoped Todos, including business hours validation."""

    @staticmethod
    def _validate_within_business_hours(
        tenant: Tenant,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
    ) -> None:
        """
        Validates that the given start_time and end_time fall within the Tenant's configured
        business hours in the tenant's timezone. Raises DRF ValidationError if outside business hours.
        """
        if not start_time and not end_time:
            return

        tenant_tz = zoneinfo.ZoneInfo(tenant.timezone)

        for label, dt in [("start_time", start_time), ("end_time", end_time)]:
            if dt is not None:
                local_dt = dt.astimezone(tenant_tz)
                local_time = local_dt.time()

                if not (tenant.business_start_time <= local_time <= tenant.business_end_time):
                    raise DRFValidationError(
                        {
                            label: (
                                f"{label} ({local_time.strftime('%H:%M:%S')} {tenant.timezone}) "
                                f"must be within tenant business hours "
                                f"({tenant.business_start_time.strftime('%H:%M:%S')} - "
                                f"{tenant.business_end_time.strftime('%H:%M:%S')})."
                            )
                        }
                    )

    @staticmethod
    @_handle_django_validation
    def create_todo(tenant_id: UUID, created_by_id: UUID, **todo_data) -> Todo:
        """
        Creates a new Todo within the specified Tenant.

        - Validates that the tenant exists.
        - Verifies the creator user exists within the tenant.
        - Enforces business-hours constraints on start_time/end_time.
        - Persists the Todo via the repository layer.

        Returns the created Todo instance.
        """
        tenant = TenantService.get_tenant(tenant_id)
        # Verify user exists within this tenant
        UserService.get_user(tenant_id=tenant_id, user_id=created_by_id)

        TodoService._validate_within_business_hours(
            tenant=tenant,
            start_time=todo_data.get("start_time"),
            end_time=todo_data.get("end_time"),
        )

        return TodoRepository.create(
            tenant_id=tenant_id,
            created_by_id=created_by_id,
            **todo_data,
        )

    @staticmethod
    def get_todo(tenant_id: UUID, todo_id: UUID) -> Todo:
        """
        Retrieves a single Todo by ID within the specified Tenant.

        Raises NotFound if the Todo does not exist or does not belong to the tenant.
        """
        todo = TodoRepository.get_by_id(tenant_id=tenant_id, todo_id=todo_id)
        if not todo:
            raise NotFound(detail=f"Todo with id '{todo_id}' not found in this tenant.")
        return todo

    @staticmethod
    def list_todos(
        tenant_id: UUID,
        status: Optional[str] = None,
        created_by_id: Optional[UUID] = None,
    ) -> QuerySet[Todo]:
        """
        Lists Todos for the given Tenant, with optional filters by status and creator.

        Filters applied:
        - `status`: restrict to a specific status (e.g., "PENDING", "COMPLETED")
        - `created_by_id`: restrict to Todos created by a specific user

        Returns a QuerySet of Todo objects ordered by -created_at.
        """
        return TodoRepository.list_by_tenant(
            tenant_id=tenant_id,
            status=status,
            created_by_id=created_by_id,
        )

    @staticmethod
    @_handle_django_validation
    def update_todo(tenant_id: UUID, todo_id: UUID, **update_data) -> Todo:
        """
        Updates an existing Todo within the specified Tenant.

        Validates business-hours constraints if start_time or end_time is being modified.
        Prevents mutating ownership/tenant fields (tenant_id, created_by_id) during update.

        Returns the updated Todo instance.
        """
        existing_todo = TodoService.get_todo(tenant_id=tenant_id, todo_id=todo_id)

        # Validate business hours if start_time or end_time is being modified
        new_start = update_data.get("start_time", existing_todo.start_time)
        new_end = update_data.get("end_time", existing_todo.end_time)
        if "start_time" in update_data or "end_time" in update_data:
            TodoService._validate_within_business_hours(
                tenant=existing_todo.tenant,
                start_time=new_start,
                end_time=new_end,
            )

        updated_todo = TodoRepository.update(
            tenant_id=tenant_id,
            todo_id=todo_id,
            **update_data,
        )
        return updated_todo  # type: ignore

    @staticmethod
    @_handle_django_validation
    def change_todo_status(tenant_id: UUID, todo_id: UUID, status: Todo.Status) -> Todo:
        """
        Changes the status of a Todo within the specified Tenant.

        Returns the updated Todo instance.
        Raises NotFound if the Todo does not exist in the tenant.
        """
        todo = TodoRepository.update_status(
            tenant_id=tenant_id,
            todo_id=todo_id,
            status=status,
        )
        if not todo:
            raise NotFound(detail=f"Todo with id '{todo_id}' not found in this tenant.")
        return todo

    @staticmethod
    def delete_todo(tenant_id: UUID, todo_id: UUID) -> None:
        """
        Deletes a Todo within the specified Tenant.

        Raises NotFound if the Todo does not exist.
        """
        deleted = TodoRepository.delete(tenant_id=tenant_id, todo_id=todo_id)
        if not deleted:
            raise NotFound(detail=f"Todo with id '{todo_id}' not found in this tenant.")