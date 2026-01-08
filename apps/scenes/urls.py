from django.urls import path
from .views import GenerateScenesAPIView

urlpatterns = [
    path(
        'projects/<int:project_id>/generate-scenes/',
        GenerateScenesAPIView.as_view(),
        name='generate-scenes'
    ),
]
