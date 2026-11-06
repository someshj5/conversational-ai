
from uuid import UUID

from django.contrib.auth import get_user_model
from rest_framework.exceptions import NotAuthenticated, PermissionDenied # type: ignore

from taskapp.approval_service import TodoApprovalService
from taskapp.models import TodoCreationRequest

User = get_user_model()



def approve_todo_request(
    *,
    authenticated_user,
    request_id: UUID,
) -> TodoCreationRequest:
    """Approve a pending Todo request owned by the authenticated user."""

    if (
        authenticated_user is None
        or not authenticated_user.is_authenticated
    ):
        raise NotAuthenticated("Authentication is required.")

    request = (
        TodoCreationRequest.objects
        .filter(
            id=request_id,
            tenant_id=authenticated_user.tenant_id,
            created_by_id=authenticated_user.id,
        )
        .first()
    )

    if request is None:
        # Do not disclose requests belonging to another user or tenant.
        raise PermissionDenied(
            "This Todo request cannot be approved by the current user."
        )

    return TodoApprovalService.approve(
        request_id=request.id,
        tenant_id=authenticated_user.tenant_id,
        created_by_id=authenticated_user.id,
    )
