from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render   # 🔥 THIS WAS MISSING

from rest_framework.routers import DefaultRouter
from apps.projects.views import ProjectViewSet
from apps.stories.views import StoryViewSet

router = DefaultRouter()
router.register(r"projects", ProjectViewSet, basename="project")
router.register(r"stories", StoryViewSet, basename="story")


def scene_editor_view(request):
    return render(request, "scene_editor.html")


urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/", include(router.urls)),
    path("", include("apps.scenes.urls")),

    path("editor/", scene_editor_view, name="scene_editor"),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
