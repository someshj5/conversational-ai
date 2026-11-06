
from uuid import UUID

import os
import django
from pathlib import Path
from dotenv import load_dotenv
from langchain.tools import tool
from rest_framework.exceptions import APIException, NotFound # type: ignore
from django.core.exceptions import ValidationError as DjangoValidationError

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from taskapp.approval_service import TodoApprovalService
from taskapp.models import TodoCreationRequest


def make_todo_tools(*, tenant_id: UUID, created_by_id: UUID):
    """Build Todo tools bound to trusted application identity."""

    # Validate the trusted context when constructing the tools.
    tenant_uuid = UUID(str(tenant_id))
    creator_uuid = UUID(str(created_by_id))

    @tool
    def prepare_todo(
        title: str,
        description: str = "",
        start_time: str | None = None,
        end_time: str | None = None,
        status: str = "PENDING",
    ) -> str:
        """Prepare a Todo proposal for review without creating the Todo.

        Use this tool when the user asks to create a Todo. Show the returned
        preview and request explicit user approval through the application.
        Never claim that the Todo has been created at this stage.
        """
        try:
            request = TodoApprovalService.prepare(
                tenant_id=tenant_uuid,
                created_by_id=creator_uuid,
                title=title,
                description=description,
                start_time=start_time,
                end_time=end_time,
                status=status,
            )
            return (
                "Todo proposal prepared; no Todo has been created.\n"
                f"request_id: {request.id}\n"
                f"state: {request.state}\n"
                f"proposal: {request.payload}"
            )
        except (ValueError, TypeError, DjangoValidationError, APIException) as exc:
            return f"Todo proposal rejected: {exc}"

    @tool
    def execute_todo(request_id: str) -> str:
        """Execute a previously approved Todo request.

        This tool cannot approve requests. The request must already have
        been explicitly approved by trusted application code.
        """
        try:
            request_uuid = UUID(request_id)
            todo = TodoApprovalService.execute(
                request_id=request_uuid,
                tenant_id=tenant_uuid,
                created_by_id=creator_uuid,
            )
            return (
                "Todo created successfully.\n"
                f"id: {todo.id}\n"
                f"title: {todo.title}\n"
                f"status: {todo.status}"
            )
        except (ValueError, TypeError, DjangoValidationError, APIException) as exc:
            return f"Todo execution failed: {exc}"

    return [prepare_todo, execute_todo]
