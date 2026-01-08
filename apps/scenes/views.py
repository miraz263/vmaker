from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.stories.models import Story
from apps.scenes.models import Scene
from apps.ai_engine.services import generate_scenes_from_story


class GenerateScenesAPIView(APIView):
    def post(self, request, project_id):
        # 1. Get story from DB
        try:
            story = Story.objects.get(project_id=project_id)
        except Story.DoesNotExist:
            return Response(
                {"error": "Story not found for this project"},
                status=status.HTTP_404_NOT_FOUND
            )

        # 2. Generate scenes from AI
        scenes_data = generate_scenes_from_story(story.text)

        # 3. Delete old scenes
        Scene.objects.filter(project_id=project_id).delete()

        # 4. Save new scenes
        saved_scenes = []
        for scene in scenes_data:
            obj = Scene.objects.create(
                project_id=project_id,
                data=scene
            )
            saved_scenes.append(obj.data)

        # 5. Response
        return Response(
            {
                "project_id": project_id,
                "scene_count": len(saved_scenes),
                "scenes": saved_scenes
            },
            status=status.HTTP_201_CREATED
        )
