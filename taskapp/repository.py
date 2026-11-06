from typing import Optional
from uuid import UUID
from django.db import transaction
from django.db.models import QuerySet
from .models import  Todo


class TodoRepository:
    """Data access layer for Tenant-scoped Todo CRUD operations."""

    @staticmethod
    @transaction.atomic
    def create(tenant_id: UUID, created_by_id: UUID, **todo_data) -> Todo:
        """
        Creates a new Todo record in the database.

        - Constructs a Todo instance with the provided tenant, creator, and field data.
        - Runs full clean validation (model-level validation including timezone and time-range checks).
        - Saves the record and returns the persisted Todo instance.
        """
        todo = Todo(
            tenant_id=tenant_id,
            created_by_id=created_by_id,
            **todo_data,
        )
        todo.full_clean()
        todo.save()
        return todo

    @staticmethod
    def get_by_id(tenant_id: UUID, todo_id: UUID) -> Optional[Todo]:
        """
        Retrieves a single Todo by ID for the given Tenant.

        Uses `select_related` for tenant and created_by to reduce DB queries.
        Returns None if no matching Todo exists.
        """
        return (
            Todo.objects.select_related("tenant", "created_by")
            .filter(tenant_id=tenant_id, id=todo_id)
            .first()
        )

    @staticmethod
    def list_by_tenant(
        tenant_id: UUID,
        status: Optional[str] = None,
        created_by_id: Optional[UUID] = None,
    ) -> QuerySet[Todo]:
        """
        Lists Todos for the given Tenant, with optional filtering.

        Filters applied:
        - `status`: restrict to a specific status (e.g., "PENDING", "COMPLETED")
        - `created_by_id`: restrict to Todos created by a specific user

        Uses `select_related` for tenant and created_by. Returns a QuerySet ordered by -created_at
        (ordering defined in the Todo model Meta class).
        """
        queryset = Todo.objects.select_related("tenant", "created_by").filter(
            tenant_id=tenant_id
        )
        if status:
            queryset = queryset.filter(status=status)
        if created_by_id:
            queryset = queryset.filter(created_by_id=created_by_id)
        return queryset

    @staticmethod
    @transaction.atomic
    def update(tenant_id: UUID, todo_id: UUID, **update_data) -> Optional[Todo]:
        """
        Updates an existing Todo record.

        - Retrieves the Todo by ID; returns None if not found.
        - Strips out ownership/tenant fields (tenant_id, tenant, created_by_id, created_by) to prevent
          accidental mutation of ownership.
        - Runs full clean validation before saving.
        - Saves with only the updated fields plus updated_at.

        Returns the updated Todo instance, or None if not found.
        """
        todo = TodoRepository.get_by_id(tenant_id, todo_id)
        if not todo:
            return None

        # Prevent mutating ownership/tenant fields during standard update
        update_data.pop("tenant_id", None)
        update_data.pop("tenant", None)
        update_data.pop("created_by_id", None)
        update_data.pop("created_by", None)

        for field, value in update_data.items():
            setattr(todo, field, value)

        todo.full_clean()
        todo.save(update_fields=[*update_data.keys(), "updated_at"])
        return todo

    @staticmethod
    def update_status(
        tenant_id: UUID, todo_id: UUID, status: Todo.Status
    ) -> Optional[Todo]:
        """
        Updates only the status field of a Todo.

        Delegates to the generic `update` method with `status=status`.
        Returns the updated Todo instance, or None if not found.
        """
        return TodoRepository.update(tenant_id, todo_id, status=status)

    @staticmethod
    def delete(tenant_id: UUID, todo_id: UUID) -> bool:
        """
        Deletes all Todo records matching the given tenant_id and todo_id.

        Returns True if at least one record was deleted, False otherwise.
        """
        deleted_count, _ = Todo.objects.filter(
            tenant_id=tenant_id, id=todo_id
        ).delete()
        return deleted_count > 0