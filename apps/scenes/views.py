from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from apps.stories.models import Story
from apps.scenes.models import Scene
from apps.ai_engine.services import generate_scenes_from_story


@method_decorator(csrf_exempt, name="dispatch")
class GenerateScenesAPIView(APIView):
    def post(self, request, project_id):

        # ===============================
        # 1️⃣ Get story text
        # ===============================
        story_text = request.data.get("story")

        if story_text:
            source = "request"
            story_id = None
        else:
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

        # ===============================
        # 2️⃣ Generate scenes (AI ENGINE)
        # ===============================
        scenes_data = generate_scenes_from_story(story_text)

        if not isinstance(scenes_data, list):
            return Response(
                {"error": "Scene generation failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # ===============================
        # 3️⃣ Save scenes (🔥 HARD DEDUP HERE)
        # ===============================
        with transaction.atomic():
            Scene.objects.filter(project_id=project_id).delete()

            saved = []
            for idx, scene in enumerate(scenes_data, start=1):

                # 🔥 FINAL SAFETY: deduplicate characters by key
                characters = scene.get("characters", [])
                if isinstance(characters, list):
                    scene["characters"] = list({
                        c.get("key"): c for c in characters if isinstance(c, dict)
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

        # ===============================
        # 4️⃣ Response
        # ===============================
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
