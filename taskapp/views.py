
from uuid import UUID

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status # type: ignore
from rest_framework.authentication import SessionAuthentication # type: ignore
from rest_framework.exceptions import APIException, NotFound, PermissionDenied # type: ignore
from rest_framework.permissions import IsAuthenticated # type: ignore
from rest_framework.response import Response # type: ignore
from rest_framework.views import APIView # type: ignore

from taskapp.approval_handlers import approve_todo_request
from taskapp.models import TodoCreationRequest


class TodoApprovalView(APIView):
    """
    Approve a pending Todo proposal belonging to the authenticated user.
    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, request_id: UUID):
        try:
            approved_request = approve_todo_request(
                authenticated_user=request.user,
                request_id=request_id,
            )
        except PermissionDenied:
            raise
        except NotFound:
            raise
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )
        except (DjangoValidationError, APIException):
            raise

        return Response(
            {
                "request_id": str(approved_request.id),
                "state": approved_request.state,
                "payload": approved_request.payload,
                "approved_at": approved_request.approved_at.isoformat(), # type: ignore
            },
            status=status.HTTP_200_OK,
        )
