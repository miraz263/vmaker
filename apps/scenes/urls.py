from django.urls import path
from .views import (
    GenerateScenesAPIView,
    SceneListAPIView,
    SceneAnimationAPIView,
    animation_player_view
)

urlpatterns = [
    path(
        "api/projects/<int:project_id>/generate-scenes/",
        GenerateScenesAPIView.as_view()
    ),
    path(
        "api/projects/<int:project_id>/scenes/",
        SceneListAPIView.as_view()
    ),
    path(
        "api/scenes/<int:scene_id>/animation/",
        SceneAnimationAPIView.as_view()
    ),
    path(
        "animation/player/",
        animation_player_view
    ),
]
