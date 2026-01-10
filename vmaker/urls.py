"""
URL configuration for vmaker project.
"""

from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render
from rest_framework.routers import DefaultRouter

from django.conf import settings
from django.conf.urls.static import static

from apps.projects.views import ProjectViewSet
from apps.stories.views import StoryViewSet

# -------------------
# DRF Router
# -------------------
router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'stories', StoryViewSet, basename='story')

# -------------------
# Template-based view
# -------------------
def scene_editor(request):
    return render(request, "scene_editor.html")

# -------------------
# URL Patterns
# -------------------
urlpatterns = [
    path('admin/', admin.site.urls),

    # API routes
    path('api/', include(router.urls)),
    path('api/', include('apps.scenes.urls')),

    # Web pages
    path('editor/', scene_editor, name='scene_editor'),
]

# -------------------
# Media files (DEV only)
# -------------------
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
