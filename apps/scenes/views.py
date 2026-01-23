from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.shortcuts import render
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from apps.stories.models import Story
from apps.scenes.models import Scene
from apps.ai_engine.services import generate_scenes_from_story
from .animation.generator import generate_scene_animation


# =========================================================
# Generate Scenes from Story
# =========================================================
@method_decorator(csrf_exempt, name="dispatch")
class GenerateScenesAPIView(APIView):
    def post(self, request, project_id):

        story_text = request.data.get("story")
        story_id = None

        if not story_text:
            story = (
                Story.objects
                .filter(project_id=project_id)
                .order_by("-id")
                .first()
            )
            if not story:
                return Response(
                    {"error": "No story found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            story_text = story.text
            story_id = story.id
            source = "database"
        else:
            source = "request"

        scenes_data = generate_scenes_from_story(story_text)

        if not isinstance(scenes_data, list):
            return Response(
                {"error": "Scene generation failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        with transaction.atomic():
            Scene.objects.filter(project_id=project_id).delete()

            saved = []
            for idx, scene in enumerate(scenes_data, start=1):

                characters = scene.get("characters", [])
                if isinstance(characters, list):
                    scene["characters"] = list({
                        c.get("key"): c
                        for c in characters
                        if isinstance(c, dict) and c.get("key")
                    }.values())

                obj = Scene.objects.create(
                    project_id=project_id,
                    order=idx,
                    data=scene
                )

                saved.append({
                    "id": obj.id,
                    **obj.data
                })

        return Response(
            {
                "project_id": project_id,
                "story_id": story_id,
                "scene_count": len(saved),
                "scenes": saved,
                "source": source
            },
            status=status.HTTP_201_CREATED
        )


# =========================================================
# Scene List API  (🔥 REQUIRED)
# =========================================================
class SceneListAPIView(APIView):
    def get(self, request, project_id):
        scenes = (
            Scene.objects
            .filter(project_id=project_id)
            .order_by("order")
            .values("id", "order")
        )
        return Response(list(scenes), status=status.HTTP_200_OK)


# =========================================================
# Scene Animation API
# =========================================================
class SceneAnimationAPIView(APIView):
    def get(self, request, scene_id):
        try:
            scene = Scene.objects.get(id=scene_id)
            animation_json = generate_scene_animation(scene)
            return Response(animation_json)

        except Scene.DoesNotExist:
            return Response(
                {"error": "Scene not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:
            return Response(
                {
                    "error": "Animation generation failed",
                    "details": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# =========================================================
# Animation Player Page
# =========================================================
def animation_player_view(request):
    return render(request, "animation_player.html")
