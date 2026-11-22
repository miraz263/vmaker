from django.urls import path
from .views import (
    StartRenderAPIView,
    RenderJobStatusAPIView,
    ProjectRenderHistoryAPIView
)

urlpatterns = [
    path("api/projects/<int:project_id>/render/", StartRenderAPIView.as_view(), name="start-project-render"),
    path("api/projects/<int:project_id>/renders/", ProjectRenderHistoryAPIView.as_view(), name="project-render-history"),
    path("api/render-jobs/<uuid:job_id>/", RenderJobStatusAPIView.as_view(), name="render-job-status"),
]
