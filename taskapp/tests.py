
from django.test import TestCase

from taskapp.approval_service import TodoApprovalService
from taskapp.models import Todo, TodoCreationRequest
from user_management.models import Tenant, User
from rest_framework.exceptions import NotAuthenticated, PermissionDenied # type: ignore
from taskapp.approval_handlers import approve_todo_request
from rest_framework.test import APIClient # type: ignore
from django.urls import reverse

class TodoApprovalServiceTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Approval Test Tenant",
            timezone="UTC",
            business_start_time="09:00",
            business_end_time="17:00",
        )
        self.user = User.objects.create_user(
            username="approval_test_user",
            password="test-password",
            tenant=self.tenant,
        )

    def test_prepare_creates_pending_request_without_creating_todo(self):
        initial_todo_count = Todo.objects.count()

        request = TodoApprovalService.prepare(
            tenant_id=self.tenant.id,
            created_by_id=self.user.id,
            title="Review database indexes",
            description="Review multi-tenant query performance.",
        )

        self.assertEqual(request.state, TodoCreationRequest.State.PENDING)
        self.assertEqual(request.tenant_id, self.tenant.id) # type: ignore
        self.assertEqual(request.created_by_id, self.user.id) # type: ignore
        self.assertEqual(request.payload["title"], "Review database indexes")
        self.assertEqual(Todo.objects.count(), initial_todo_count)

    def test_prepare_rejects_invalid_time_range(self):
        initial_request_count = TodoCreationRequest.objects.count()
        initial_todo_count = Todo.objects.count()

        with self.assertRaisesRegex(
            ValueError,
            "end_time must be after start_time",
        ):
            TodoApprovalService.prepare(
                tenant_id=self.tenant.id,
                created_by_id=self.user.id,
                title="Invalid schedule",
                start_time="2026-10-30T15:00:00+00:00",
                end_time="2026-10-30T14:00:00+00:00",
            )

        self.assertEqual(
            TodoCreationRequest.objects.count(),
            initial_request_count,
        )
        self.assertEqual(Todo.objects.count(), initial_todo_count)


    def test_unauthenticated_user_cannot_approve_request(self):
        request = TodoApprovalService.prepare(
            tenant_id=self.tenant.id,
            created_by_id=self.user.id,
            title="Private Todo",
        )

        with self.assertRaises(NotAuthenticated):
            approve_todo_request(
                authenticated_user=None,
                request_id=request.id,
            )

        request.refresh_from_db()
        self.assertEqual(request.state, TodoCreationRequest.State.PENDING)

    def test_another_user_in_same_tenant_cannot_approve_request(self):
        other_user = User.objects.create_user(
            username="another_user",
            password="test-password",
            tenant=self.tenant,
        )
        request = TodoApprovalService.prepare(
            tenant_id=self.tenant.id,
            created_by_id=self.user.id,
            title="Private Todo",
        )

        with self.assertRaises(PermissionDenied):
            approve_todo_request(
                authenticated_user=other_user,
                request_id=request.id,
            )

        request.refresh_from_db()
        self.assertEqual(request.state, TodoCreationRequest.State.PENDING)

    def test_user_from_another_tenant_cannot_approve_request(self):
        other_tenant = Tenant.objects.create(
            name="Another Tenant",
            timezone="UTC",
            business_start_time="09:00",
            business_end_time="17:00",
        )
        other_user = User.objects.create_user(
            username="other_tenant_user",
            password="test-password",
            tenant=other_tenant,
        )
        request = TodoApprovalService.prepare(
            tenant_id=self.tenant.id,
            created_by_id=self.user.id,
            title="Private Todo",
        )

        with self.assertRaises(PermissionDenied):
            approve_todo_request(
                authenticated_user=other_user,
                request_id=request.id,
            )

        request.refresh_from_db()
        self.assertEqual(request.state, TodoCreationRequest.State.PENDING)

    def test_approved_request_creates_todo_and_becomes_consumed(self):
        request = TodoApprovalService.prepare(
            tenant_id=self.tenant.id,
            created_by_id=self.user.id,
            title="Review database indexes",
        )

        approved = TodoApprovalService.approve(
            request_id=request.id,
            tenant_id=self.tenant.id,
            created_by_id=self.user.id,
        )

        self.assertEqual(
            approved.state,
            TodoCreationRequest.State.APPROVED,
        )
        self.assertEqual(Todo.objects.count(), 0)

        todo = TodoApprovalService.execute(
            request_id=request.id,
            tenant_id=self.tenant.id,
            created_by_id=self.user.id,
        )

        approved.refresh_from_db()
        self.assertEqual(todo.title, "Review database indexes")
        self.assertEqual(approved.state, TodoCreationRequest.State.CONSUMED)
        self.assertEqual(Todo.objects.count(), 1)
        self.assertIsNotNone(approved.consumed_at)

    def test_unapproved_request_cannot_execute(self):
        request = TodoApprovalService.prepare(
            tenant_id=self.tenant.id,
            created_by_id=self.user.id,
            title="Unapproved Todo",
        )

        with self.assertRaisesRegex(
            ValueError,
            "Only approved, unused requests can be executed",
        ):
            TodoApprovalService.execute(
                request_id=request.id,
                tenant_id=self.tenant.id,
                created_by_id=self.user.id,
            )

        self.assertEqual(Todo.objects.count(), 0)

    def test_consumed_request_cannot_execute_twice(self):
        request = TodoApprovalService.prepare(
            tenant_id=self.tenant.id,
            created_by_id=self.user.id,
            title="One-time Todo",
        )

        TodoApprovalService.approve(
            request_id=request.id,
            tenant_id=self.tenant.id,
            created_by_id=self.user.id,
        )
        TodoApprovalService.execute(
            request_id=request.id,
            tenant_id=self.tenant.id,
            created_by_id=self.user.id,
        )

        with self.assertRaisesRegex(
            ValueError,
            "Only approved, unused requests can be executed",
        ):
            TodoApprovalService.execute(
                request_id=request.id,
                tenant_id=self.tenant.id,
                created_by_id=self.user.id,
            )

        self.assertEqual(Todo.objects.count(), 1)


class TodoApprovalAPITests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Approval API Tenant",
            timezone="UTC",
            business_start_time="09:00",
            business_end_time="17:00",
        )
        self.user = User.objects.create_user(
            username="approval_api_user",
            password="test-password",
            tenant=self.tenant,
        )
        self.client = APIClient()
        self.url_name = "todo-creation-request-approve"

    def create_pending_request(self):
        return TodoApprovalService.prepare(
            tenant_id=self.tenant.id,
            created_by_id=self.user.id,
            title="API approval test",
        )

    def test_unauthenticated_request_is_rejected(self):
        request = self.create_pending_request()

        response = self.client.post(
            reverse(self.url_name, kwargs={"request_id": request.id}),
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        request.refresh_from_db()
        self.assertEqual(request.state, TodoCreationRequest.State.PENDING)

    def test_authenticated_user_can_approve_request(self):
        request = self.create_pending_request()
        self.client.force_authenticate(user=self.user) # type: ignore

        response = self.client.post(
            reverse(self.url_name, kwargs={"request_id": request.id}),
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["state"], TodoCreationRequest.State.APPROVED) # type: ignore
        self.assertEqual(response.data["request_id"], str(request.id)) # type: ignore

        request.refresh_from_db()
        self.assertEqual(request.state, TodoCreationRequest.State.APPROVED)
        self.assertEqual(Todo.objects.count(), 0)

    def test_another_user_cannot_approve_request(self):
        request = self.create_pending_request()
        other_user = User.objects.create_user(
            username="another_approval_api_user",
            password="test-password",
            tenant=self.tenant,
        )
        self.client.force_authenticate(user=other_user) # type: ignore

        response = self.client.post(
            reverse(self.url_name, kwargs={"request_id": request.id}),
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        request.refresh_from_db()
        self.assertEqual(request.state, TodoCreationRequest.State.PENDING)

    def test_approved_request_cannot_be_approved_again(self):
        request = self.create_pending_request()
        self.client.force_authenticate(user=self.user)# type: ignore

        first_response = self.client.post(
            reverse(self.url_name, kwargs={"request_id": request.id}),
            format="json",
        )
        second_response = self.client.post(
            reverse(self.url_name, kwargs={"request_id": request.id}),
            format="json",
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 409)
        self.assertEqual(Todo.objects.count(), 0)
