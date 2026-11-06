
from uuid import UUID
from django.db.models import QuerySet
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import NotFound, ValidationError as DRFValidationError # type: ignore

from .models import Tenant, User
from .repository import TenantRepository, UserRepository


def _handle_django_validation(func):
    """Decorator to convert Django's ValidationError into DRF's ValidationError."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except DjangoValidationError as exc:
            raise DRFValidationError(detail=exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
    return wrapper


class TenantService:
    """Business logic for managing Tenants."""

    @staticmethod
    @_handle_django_validation
    def create_tenant(**data) -> Tenant:
        """
        Creates a new Tenant.

        Validates input data (timezone format, business hours ordering) via the
        ``_handle_django_validation`` decorator before persisting via the repository.
        """
        return TenantRepository.create(**data)

    @staticmethod
    def get_tenant(tenant_id: UUID) -> Tenant:
        """
        Retrieves a Tenant by ID.

        Raises ``NotFound`` if the tenant does not exist.
        """
        tenant = TenantRepository.get_by_id(tenant_id)
        if not tenant:
            raise NotFound(detail=f"Tenant with id '{tenant_id}' not found.")
        return tenant

    @staticmethod
    def get_tenant_by_name(name: str) -> Tenant:
        """
        Retrieves a Tenant by name.

        Raises ``NotFound`` if no tenant with the given name exists.
        """
        tenant = TenantRepository.get_by_name(name)
        if not tenant:
            raise NotFound(detail=f"Tenant with id '{name}' not found.")
        return tenant

    @staticmethod
    def list_tenants() -> QuerySet[Tenant]:
        """Returns a QuerySet of all Tenant objects."""
        return TenantRepository.list_all()

    @staticmethod
    @_handle_django_validation
    def update_tenant(tenant_id: UUID, **update_data) -> Tenant:
        """
        Updates a Tenant by ID.

        Validates input data before persisting changes. Raises ``NotFound`` if the tenant
        does not exist.
        """
        tenant = TenantRepository.update(tenant_id, **update_data)
        if not tenant:
            raise NotFound(detail=f"Tenant with id '{tenant_id}' not found.")
        return tenant

    @staticmethod
    def delete_tenant(tenant_id: UUID) -> None:
        """
        Deletes a Tenant by ID.

        Raises ``NotFound`` if the tenant does not exist.
        """
        deleted = TenantRepository.delete(tenant_id)
        if not deleted:
            raise NotFound(detail=f"Tenant with id '{tenant_id}' not found.")


class UserService:
    """Business logic for managing Tenant-scoped Users."""

    @staticmethod
    @_handle_django_validation
    def create_user(tenant_id: UUID, password: str, **user_data) -> User:
        """
        Creates a new User within the specified Tenant.

        - Ensures the tenant exists before creating the user.
        - Hashes the provided password (or sets unusable password if none provided).
        - Raises ``NotFound`` if the tenant does not exist.
        - Raises Django ``ValidationError`` (converted to DRF ``ValidationError``) if data is invalid.

        Returns the created User instance.
        """
        # Ensure tenant exists before creating user
        TenantService.get_tenant(tenant_id)
        return UserRepository.create(
            tenant_id=tenant_id,
            password=password,
            **user_data,
        )

    @staticmethod
    def get_user(tenant_id: UUID, user_id: UUID) -> User:
        """
        Retrieves a User by ID within the specified Tenant.

        Raises ``NotFound`` if the user does not exist in the tenant.
        """
        user = UserRepository.get_by_id(tenant_id=tenant_id, user_id=user_id)
        if not user:
            raise NotFound(detail=f"User with id '{user_id}' not found in this tenant.")
        return user

    @staticmethod
    def list_users(tenant_id: UUID) -> QuerySet[User]:
        """Returns a QuerySet of all Users belonging to the given Tenant."""
        return UserRepository.list_by_tenant(tenant_id=tenant_id)

    @staticmethod
    @_handle_django_validation
    def update_user(tenant_id: UUID, user_id: UUID, **update_data) -> User:
        """
        Updates a User within the specified Tenant.

        - Validates input data before persisting.
        - Handles password re-hashing if a new password is provided.
        - Raises ``NotFound`` if the user does not exist in the tenant.

        Returns the updated User instance.
        """
        user = UserRepository.update(tenant_id=tenant_id, user_id=user_id, **update_data)
        if not user:
            raise NotFound(detail=f"User with id '{user_id}' not found in this tenant.")
        return user

    @staticmethod
    def delete_user(tenant_id: UUID, user_id: UUID) -> None:
        """
        Deletes a User within the specified Tenant.

        Raises ``NotFound`` if the user does not exist in the tenant.
        """
        deleted = UserRepository.delete(tenant_id=tenant_id, user_id=user_id)
        if not deleted:
            raise NotFound(detail=f"User with id '{user_id}' not found in this tenant.")

