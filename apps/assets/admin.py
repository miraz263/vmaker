from django.contrib import admin
from .models import Character, CharacterAsset, Asset3D, AnimationClip


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ("id", "name")


@admin.register(CharacterAsset)
class CharacterAssetAdmin(admin.ModelAdmin):
    list_display = ("id", "character", "pose", "image")


@admin.register(Asset3D)
class Asset3DAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category", "file", "has_visemes", "created_at")
    list_filter = ("category", "has_visemes")
    search_fields = ("name",)


@admin.register(AnimationClip)
class AnimationClipAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "clip_file", "duration", "loop")
    search_fields = ("name",)
