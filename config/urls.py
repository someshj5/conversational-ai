
from django.contrib import admin
from django.urls import path,include

from taskapp.views import TodoApprovalView

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "api/todo-creation-requests/<uuid:request_id>/approve/",
        TodoApprovalView.as_view(),
        name="todo-creation-request-approve",
    ),
    path("api/", include("agent_api.urls")),
]



