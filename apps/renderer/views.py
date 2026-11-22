import threading
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.projects.models import Project
from .models import RenderJob
from .serializers import RenderJobSerializer
from .tasks import render_project_video_task


class StartRenderAPIView(APIView):
    """
    POST /api/projects/<project_id>/render/
    Dispatches a background render job for the project's scenes.
    """
    def post(self, request, project_id):
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response(
                {"error": "Project not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        resolution = request.data.get("resolution", "1080p")
        fps = int(request.data.get("fps", 24))

        job = RenderJob.objects.create(
            project=project,
            resolution=resolution,
            fps=fps,
            status="QUEUED",
            progress=0
        )

        # Dispatch Celery task
        try:
            render_project_video_task.delay(str(job.id))
        except Exception:
            # Fallback for dev environments where Celery/Redis worker is offline: run in thread
            threading.Thread(
                target=render_project_video_task,
                args=(str(job.id),),
                daemon=True
            ).start()

        return Response(
            {
                "job_id": job.id,
                "project_id": project.id,
                "status": job.status,
                "progress": job.progress,
                "status_url": f"/api/render-jobs/{job.id}/"
            },
            status=status.HTTP_202_ACCEPTED
        )


class RenderJobStatusAPIView(APIView):
    """
    GET /api/render-jobs/<job_id>/
    Polls real-time rendering status and progress (0% - 100%).
    """
    def get(self, request, job_id):
        try:
            job = RenderJob.objects.get(id=job_id)
        except RenderJob.DoesNotExist:
            return Response(
                {"error": "Render job not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = RenderJobSerializer(job)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProjectRenderHistoryAPIView(APIView):
    """
    GET /api/projects/<project_id>/renders/
    Lists past render jobs for a project.
    """
    def get(self, request, project_id):
        jobs = RenderJob.objects.filter(project_id=project_id)
        serializer = RenderJobSerializer(jobs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
