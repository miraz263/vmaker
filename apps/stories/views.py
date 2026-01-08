from rest_framework.viewsets import ModelViewSet
from .models import Story
from .serializers import StorySerializer

class StoryViewSet(ModelViewSet):
    queryset = Story.objects.all()
    serializer_class = StorySerializer
