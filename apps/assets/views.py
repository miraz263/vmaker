from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Asset3D, AnimationClip
from .serializers import Asset3DSerializer, AnimationClipSerializer


class Asset3DListView(APIView):
    """
    GET /api/assets/3d/
    Optional filter: ?category=character or ?category=environment
    """
    def get(self, request):
        category = request.query_params.get("category")
        queryset = Asset3D.objects.all()
        if category:
            queryset = queryset.filter(category=category)

        serializer = Asset3DSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AnimationClipListView(APIView):
    """
    GET /api/assets/animations/
    Lists all available skeletal animation tracks
    """
    def get(self, request):
        clips = AnimationClip.objects.all()
        serializer = AnimationClipSerializer(clips, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
