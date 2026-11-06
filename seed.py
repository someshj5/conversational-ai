from datetime import time, datetime, timezone
import os
import django
# 1. Configure Django BEFORE importing models or services
# Replace "your_project_name.settings" with the folder name containing your settings.py
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from user_management.service import TenantService, UserService
from taskapp.service import TenantService, UserService, TodoService
from taskapp.models import Todo

# 1. Create a Tenant (IST timezone, 9:00 AM to 6:00 PM business hours)
# tenant = TenantService.create_tenant(
#     name="Acme Corp",
#     timezone="Asia/Kolkata",
#     business_start_time=time(9, 0),
#     business_end_time=time(18, 0),
# )

# # 2. Create a User scoped to the Tenant
# user = UserService.create_user(
#     tenant_id=tenant.id,
#     username="rahul",
#     email="rahul@acme.com",
#     password="StrongPassword123!",
# )

# # 3. Create a Todo (05:00 UTC == 10:30 IST -> Valid within 09:00-18:00 IST)
# todo = TodoService.create_todo(
#     tenant_id=tenant.id,
#     created_by_id=user.id,
#     title="Quarterly Architecture Review",
#     description="Review multi-tenant database indexes.",
#     start_time=datetime(2026, 11, 2, 5, 0, tzinfo=timezone.utc),
#     end_time=datetime(2026, 11, 2, 6, 30, tzinfo=timezone.utc),
# )

# # 4. Update Todo Status
# updated_todo = TodoService.change_todo_status(
#     tenant_id=tenant.id,
#     todo_id=todo.id,
#     status=Todo.Status.IN_PROGRESS,
# )

# tenant = TenantService.get_tenant(tenant_id="ed7d05ef-33b7-4f41-aaf6-2e1d018151ee")
tenant = TenantService.get_tenant_by_name(name="Acme Corp")
print(tenant)
# 5. List Tenant Todos by Status
in_progress_todos = TodoService.list_todos(
    tenant_id=tenant.id,
    status=Todo.Status.IN_PROGRESS,
)
print(in_progress_todos)