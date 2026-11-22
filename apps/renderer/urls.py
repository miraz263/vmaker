from django.urls import path
from .views import (
    StartRenderAPIView,
    RenderJobStatusAPIView,
    ProjectRenderHistoryAPIView,
    AutoStoryToVideoAPIView,
    Save3DVideoAPIView
)

urlpatterns = [
    path("api/auto-video/", AutoStoryToVideoAPIView.as_view(), name="auto-story-to-video"),
    path("api/save-3d-video/", Save3DVideoAPIView.as_view(), name="save-3d-video"),
    path("api/projects/<int:project_id>/render/", StartRenderAPIView.as_view(), name="start-project-render"),
    path("api/projects/<int:project_id>/renders/", ProjectRenderHistoryAPIView.as_view(), name="project-render-history"),
    path("api/render-jobs/<uuid:job_id>/", RenderJobStatusAPIView.as_view(), name="render-job-status"),
]
