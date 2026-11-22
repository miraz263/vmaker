from django.urls import path
from .views import (
    VoiceListAPIView,
    GenerateSceneAudioAPIView,
    SceneAudioDetailAPIView
)

urlpatterns = [
    path("api/audio/voices/", VoiceListAPIView.as_view(), name="audio-voices"),
    path("api/scenes/<int:scene_id>/generate-audio/", GenerateSceneAudioAPIView.as_view(), name="scene-generate-audio"),
    path("api/scenes/<int:scene_id>/audio/", SceneAudioDetailAPIView.as_view(), name="scene-audio-detail"),
]
