from rest_framework import serializers
from .models import Asset3D, AnimationClip, Character, CharacterAsset


class Asset3DSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Asset3D
        fields = ["id", "name", "category", "file", "file_url", "thumbnail", "has_visemes", "metadata", "created_at"]

    def get_file_url(self, obj):
        return obj.file.url if obj.file else None


class AnimationClipSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnimationClip
        fields = ["id", "name", "clip_file", "duration", "loop"]
