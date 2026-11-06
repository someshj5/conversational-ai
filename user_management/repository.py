from typing import Optional
from uuid import UUID
from django.db import transaction
from django.db.models import QuerySet
from django.core.exceptions import ObjectDoesNotExist
from .models import Tenant, User


class TenantRepository:
    """Data access layer for Tenant CRUD operations."""

    @staticmethod
    def create(**data) -> Tenant:
        """
        Creates a new Tenant instance.

        - Instantiates ``Tenant`` with the provided keyword arguments.
        - Runs full model validation (timezone validity, business hours ordering).
        - Saves and returns the persisted Tenant instance.
        """
        tenant = Tenant(**data)
        tenant.full_clean()
        tenant.save()
        return tenant

    @staticmethod
    def get_by_id(tenant_id: UUID) -> Optional[Tenant]:
        """
        Retrieves a Tenant by ID.

        Returns ``None`` if no matching tenant exists.
        """
        return Tenant.objects.filter(id=tenant_id).first()

    @staticmethod
    def get_by_name(name: str) -> Optional[Tenant]:
        """
        Retrieves a Tenant by name.

        Returns ``None`` if no tenant with the given name exists.
        """
        return Tenant.objects.filter(name=name).first()

    @staticmethod
    def list_all() -> QuerySet[Tenant]:
        """Returns a QuerySet of all Tenant objects in the database."""
        return Tenant.objects.all()

    @staticmethod
    def update(tenant_id: UUID, **update_data) -> Optional[Tenant]:
        """
        Updates a Tenant by ID.

        - Retrieves the tenant; returns None if not found.
        - Applies all provided field updates.
        - Runs full clean validation before saving.
        - Returns the updated Tenant instance, or None if not found.
        """
        tenant = TenantRepository.get_by_id(tenant_id)
        if not tenant:
            return None

        for field, value in update_data.items():
            setattr(tenant, field, value)

        tenant.full_clean()
        tenant.save(update_fields=list(update_data.keys()))
        return tenant

    @staticmethod
    def delete(tenant_id: UUID) -> bool:
        """
        Deletes a Tenant by ID.

        Returns ``True`` if a record was deleted, ``False`` if no matching tenant existed.
        """
        deleted_count, _ = Tenant.objects.filter(id=tenant_id).delete()
        return deleted_count > 0


class UserRepository:
    """Data access layer for Tenant-scoped User CRUD operations."""

    @staticmethod
    @transaction.atomic
    def create(tenant_id: UUID, password: Optional[str] = None, **user_data) -> User:
        """
        Creates a new User within the specified Tenant.

        - Instantiates ``User`` with ``tenant_id`` and additional field data.
        - If ``password`` is provided, hashes it via ``set_password``; otherwise sets an unusable password.
        - Runs full model validation.
        - Saves and returns the persisted User instance.
        """
        user = User(tenant_id=tenant_id, **user_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.full_clean()
        user.save()
        return user

    @staticmethod
    def get_by_id(tenant_id: UUID, user_id: UUID) -> Optional[User]:
        """
        Retrieves a User by ID within the given Tenant.

        Uses ``select_related`` for ``tenant`` to reduce DB queries.
        Returns ``None`` if no matching user exists.
        """
        return (
            User.objects.select_related("tenant")
            .filter(tenant_id=tenant_id, id=user_id)
            .first()
        )

    @staticmethod
    def get_by_username(tenant_id: UUID, username: str) -> Optional[User]:
        """
        Retrieves a User by username within the given Tenant.

        Uses ``select_related`` for ``tenant``.
        Returns ``None`` if no matching user exists.
        """
        return (
            User.objects.select_related("tenant")
            .filter(tenant_id=tenant_id, username=username)
            .first()
        )

    @staticmethod
    def list_by_tenant(tenant_id: UUID) -> QuerySet[User]:
        """Returns a QuerySet of all Users belonging to the given Tenant."""
        return User.objects.select_related("tenant").filter(tenant_id=tenant_id)

    @staticmethod
    @transaction.atomic
    def update(tenant_id: UUID, user_id: UUID, **update_data) -> Optional[User]:
        """
        Updates a User within the specified Tenant.

        - Retrieves the user; returns None if not found.
        - If ``password`` is present in ``update_data``, re-hashes it via ``set_password``.
        - Applies all other field updates.
        - Runs full clean validation before saving.
        - Returns the updated User instance, or None if not found.
        """
        user = UserRepository.get_by_id(tenant_id, user_id)
        if not user:
            return None

        password = update_data.pop("password", None)
        if password:
            user.set_password(password)

        for field, value in update_data.items():
            setattr(user, field, value)

        user.full_clean()
        user.save()
        return user

    @staticmethod
    def delete(tenant_id: UUID, user_id: UUID) -> bool:
        """
        Deletes a User by ID within the given Tenant.

        Returns ``True`` if at least one record was deleted, ``False`` otherwise.
        """
        deleted_count, _ = User.objects.filter(
            tenant_id=tenant_id, id=user_id
        ).delete()
        return deleted_count > 0
