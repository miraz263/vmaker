from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render
from django.conf import settings
from django.conf.urls.static import static

from rest_framework.routers import DefaultRouter

from apps.projects.views import ProjectViewSet
from apps.stories.views import StoryViewSet
from apps.scenes.views import (
    GenerateScenesAPIView,
    SceneAnimationAPIView,
    animation_player_view,
)

# ===============================
# DRF Router
# ===============================
router = DefaultRouter()
router.register(r"projects", ProjectViewSet, basename="project")
router.register(r"stories", StoryViewSet, basename="story")

# ===============================
# Template Views
# ===============================
def scene_editor(request):
    return render(request, "scene_editor.html")

# ===============================
# URL Patterns (FINAL)
# ===============================
urlpatterns = [
    path("admin/", admin.site.urls),

    # -------- API --------
    path("api/", include(router.urls)),
    path(
        "api/projects/<int:project_id>/generate-scenes/",
        GenerateScenesAPIView.as_view(),
        name="generate-scenes",
    ),
    path(
        "api/scenes/<int:scene_id>/animation/",
        SceneAnimationAPIView.as_view(),
        name="scene-animation",
    ),

    # -------- Web Pages --------
    path("editor/", scene_editor, name="scene_editor"),
    path("animation/player/", animation_player_view, name="animation_player"),
]

# ===============================
# Media (DEV)
# ===============================
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
