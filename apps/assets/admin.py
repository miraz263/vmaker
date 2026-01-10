from django.contrib import admin
from .models import Character, CharacterAsset

@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ("name",)

@admin.register(CharacterAsset)
class CharacterAssetAdmin(admin.ModelAdmin):
    list_display = ("character", "pose", "image")
