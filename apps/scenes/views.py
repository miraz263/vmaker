from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction

from apps.stories.models import Story
from apps.scenes.models import Scene
from apps.ai_engine.services import generate_scenes_from_story

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


@method_decorator(csrf_exempt, name="dispatch")
class GenerateScenesAPIView(APIView):
    def post(self, request, project_id):

        # 1️⃣ Prefer story from request (live editor support)
        story_text = request.data.get("story")

        if story_text:
            source_story_text = story_text
            source_story_id = None
        else:
            # fallback to latest saved story
            story = Story.objects.filter(
                project_id=project_id
            ).order_by("-id").first()

            if not story:
                return Response(
                    {"error": "No story found for this project"},
                    status=status.HTTP_404_NOT_FOUND
                )

            source_story_text = story.text
            source_story_id = story.id

        # 2️⃣ Generate scenes from story text
        scenes_data = generate_scenes_from_story(source_story_text)

        if not scenes_data:
            return Response(
                {"error": "Scene generation failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 3️⃣ Atomic regenerate (safe)
        with transaction.atomic():
            Scene.objects.filter(project_id=project_id).delete()

            saved_scenes = []
            for idx, scene in enumerate(scenes_data, start=1):
                obj = Scene.objects.create(
                    project_id=project_id,
                    order=idx,   # timeline safe
                    data=scene
                )
                saved_scenes.append(obj.data)

        # 4️⃣ Response
        return Response(
            {
                "project_id": project_id,
                "story_id": source_story_id,
                "scene_count": len(saved_scenes),
                "scenes": saved_scenes,
                "source": "request" if story_text else "database"
            },
            status=status.HTTP_201_CREATED
        )
