
from rest_framework import serializers


class ChatMessageSerializer(serializers.Serializer):
    role = serializers.ChoiceField(
        choices=["user", "assistant"]
    )
    content = serializers.CharField(
        allow_blank=False,
        trim_whitespace=True,
    )


class ChatRequestSerializer(serializers.Serializer):
    messages = ChatMessageSerializer(
        many=True,
        allow_empty=False,
    )
