from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction

from apps.scenes.models import Scene


class UpdateSceneAPIView(APIView):
    def post(self, request, scene_id):
        """
        Update a single scene safely
        """
        try:
            scene = Scene.objects.get(id=scene_id)
        except Scene.DoesNotExist:
            return Response(
                {"error": "Scene not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        data = request.data.get("data")

        if not data:
            return Response(
                {"error": "No scene data provided"},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            scene.data = data
            scene.save(update_fields=["data"])

        return Response(
            {
                "success": True,
                "scene_id": scene.id
            },
            status=status.HTTP_200_OK
        )
