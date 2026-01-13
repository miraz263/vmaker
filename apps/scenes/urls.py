from django.urls import path
from .views import GenerateScenesAPIView
from .api import UpdateSceneAPIView

urlpatterns = [
    path(
        'projects/<int:project_id>/generate-scenes/',
        GenerateScenesAPIView.as_view(),
        name='generate-scenes'
    ),
    path(
        'scenes/<int:scene_id>/update/',
        UpdateSceneAPIView.as_view(),
        name='update-scene'
    ),
]
