from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
import uuid
import zoneinfo
from django.db import models

def validate_timezone(value: str):
    """Validates that the provided timezone string is a valid IANA timezone."""
    if value not in zoneinfo.available_timezones():
        raise ValidationError(f"'{value}' is not a valid IANA timezone.")


class Tenant(models.Model):
    """Represents a tenant organization with timezone and business-hours configuration.

    Each tenant has a unique name, an IANA timezone string, and defined business hours.
    Users are scoped to a single tenant, and all Todos are tenant-qualified.

    Fields:
        name: Human-readable tenant name (unique per tenant schema).
        timezone: Standard IANA timezone string (e.g., 'America/New_York', 'UTC').
            Validated against ``zoneinfo.available_timezones()``.
        business_start_time: Start of business hours (e.g., ``09:00:00``).
        business_end_time: End of business hours (e.g., ``17:00:00``).
            Must be after ``business_start_time``.
        created_at: Automatic timestamp when the tenant was created.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )


    name = models.CharField(max_length=255)
    timezone = models.CharField(
        max_length=63,
        default="UTC",
        validators=[validate_timezone],
        help_text="Standard IANA timezone string (e.g., 'America/New_York', 'UTC').",
    )
    business_start_time = models.TimeField(
        help_text="Start of business hours (e.g., 09:00:00)."
    )
    business_end_time = models.TimeField(
        help_text="End of business hours (e.g., 17:00:00)."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "tenants"
        verbose_name = "Tenant"
        verbose_name_plural = "Tenants"

    def clean(self):
        super().clean()
        if self.business_start_time and self.business_end_time:
            if self.business_start_time >= self.business_end_time:
                raise ValidationError("business_end_time must be after business_start_time.")

    def __str__(self):
        return self.name


class User(AbstractUser):
    """
    Custom user model inheriting from Django's AbstractUser.

    Provides standard auth fields (username, email, password, permissions)
    plus tenant association. Usernames must be unique within a single tenant.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="users",
        db_index=True,
    )

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"
        # Enforce unique usernames per tenant
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "username"],
                name="unique_tenant_username",
            )
        ]

    def __str__(self):
        return f"{self.username} ({self.tenant.name})"
