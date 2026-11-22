from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.scenes.models import Scene
from .services import create_scene_audio, BENGALI_VOICES, DEFAULT_VOICE
from .models import SceneAudio


class VoiceListAPIView(APIView):
    """List all supported neural Bengali voices."""
    def get(self, request):
        return Response({
            "default": DEFAULT_VOICE,
            "voices": BENGALI_VOICES
        }, status=status.HTTP_200_OK)


class GenerateSceneAudioAPIView(APIView):
    """
    POST /api/scenes/<scene_id>/generate-audio/
    Generates Bengali TTS audio and 3D lip-sync visemes for the scene.
    """
    def post(self, request, scene_id):
        try:
            scene = Scene.objects.get(id=scene_id)
        except Scene.DoesNotExist:
            return Response(
                {"error": "Scene not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        voice = request.data.get("voice") or request.query_params.get("voice") or DEFAULT_VOICE
        result = create_scene_audio(scene, voice=voice)
        return Response(result, status=status.HTTP_201_CREATED)


class SceneAudioDetailAPIView(APIView):
    """
    GET /api/scenes/<scene_id>/audio/
    Retrieves the existing audio track and 3D lip-sync visemes for a scene.
    """
    def get(self, request, scene_id):
        try:
            audio_track = SceneAudio.objects.get(scene_id=scene_id)
            return Response({
                "id": audio_track.id,
                "scene_id": scene_id,
                "audio_url": audio_track.audio_file.url,
                "voice": audio_track.voice,
                "duration": audio_track.duration,
                "visemes": audio_track.visemes,
            }, status=status.HTTP_200_OK)
        except SceneAudio.DoesNotExist:
            return Response(
                {"error": "Audio track not generated for this scene yet."},
                status=status.HTTP_404_NOT_FOUND
            )
