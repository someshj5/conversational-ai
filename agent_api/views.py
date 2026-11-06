
import logging
from pathlib import Path

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from agent_api.serializers import ChatRequestSerializer
from src.forge_agent.agent import create_agent
from functools import lru_cache

import json

from django.http import JsonResponse, StreamingHttpResponse
from langchain_core.messages import AIMessageChunk

from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REPOSITORY_ROOT = ROOT / "forge-agent-code" / "source"
INDEX_DIR = ROOT / "forge-agent-code" / ".code_index"


@lru_cache(maxsize=1)
def get_forge_agent():
    return create_agent(
        repository_root=REPOSITORY_ROOT,
        index_dir=INDEX_DIR,
    )

def extract_text(message):
    content = getattr(message, "content", "")

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        return "\n".join(
            block["text"]
            for block in content
            if isinstance(block, dict)
            and block.get("type") == "text"
        )

    return str(content)


class ChatView(APIView):
    # Local development only. Add authentication before deployment.
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        messages = serializer.validated_data["messages"]

        try:
            agent = get_forge_agent()

            result = agent.invoke({
                "messages": messages,
            })

            result_messages = result.get("messages", [])

            assistant_message = next(
                (
                    message
                    for message in reversed(result_messages)
                    if getattr(message, "type", None) == "ai"
                ),
                None,
            )

            if assistant_message is None:
                return Response(
                    {"error": "Agent returned no assistant response."},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            return Response({
                "reply": extract_text(assistant_message),
            })

        except Exception:
            logger.exception("Forge agent invocation failed")

            return Response(
                {"error": "The agent could not process this request."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )



def format_sse(event: str, data: dict) -> str:
    """Format one Server-Sent Event."""
    return (
        f"event: {event}\n"
        f"data: {json.dumps(data)}\n\n"
    )


def extract_chunk_text(message_chunk):
    """Extract only text content from an AI message chunk."""
    if not isinstance(message_chunk, AIMessageChunk):
        return ""

    content = message_chunk.content

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        return "".join(
            block["text"]
            for block in content
            if isinstance(block, dict)
            and block.get("type") == "text"
            and isinstance(block.get("text"), str)
        )

    return ""

@method_decorator(csrf_exempt, name="dispatch")
class ChatStreamView(View):
    permission_classes = [AllowAny]  # Local development only.

    def post(self, request):
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(
                {"error": "Invalid JSON request body."},
                status=400,
            )

        serializer = ChatRequestSerializer(data=payload)

        # serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        messages = serializer.validated_data["messages"]

        try:
            agent = get_forge_agent()
        except Exception:
            logger.exception("Forge agent initialization failed")
            return Response(
                {"error": "Forge agent could not be initialized."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        def event_stream():
            try:
                for message_chunk, metadata in agent.stream(
                    {"messages": messages},
                    stream_mode="messages",
                ):
                    text = extract_chunk_text(message_chunk)

                    if text:
                        yield format_sse(
                            "token",
                            {"content": text},
                        )

                yield format_sse("done", {"status": "completed"})

            except GeneratorExit:
                # The client disconnected.
                logger.info("Forge stream client disconnected")
                raise

            except Exception:
                logger.exception("Forge streaming invocation failed")
                yield format_sse(
                    "error",
                    {"message": "Forge encountered an error while streaming."},
                )

        response = StreamingHttpResponse(
            event_stream(),
            content_type="text/event-stream",
        )

        response["Cache-Control"] = "no-cache, no-transform"
        response["X-Accel-Buffering"] = "no"

        return response
