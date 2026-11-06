
from django.urls import path
from agent_api.views import ChatStreamView, ChatView

urlpatterns = [
    path("chat/", ChatView.as_view(), name="agent-chat"),
    path(
        "chat/stream/",
        ChatStreamView.as_view(),
        name="agent-chat-stream",
    ),
]
