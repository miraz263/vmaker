from rest_framework import serializers
from .models import RenderJob


class RenderJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = RenderJob
        fields = [
            "id",
            "project",
            "status",
            "progress",
            "resolution",
            "fps",
            "output_file",
            "video_url",
            "error_message",
            "created_at",
            "completed_at"
        ]
