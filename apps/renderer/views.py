import os
import uuid
import threading
import subprocess
from datetime import datetime
import imageio_ffmpeg
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from apps.projects.models import Project
from apps.stories.models import Story
from apps.scenes.models import Scene
from apps.ai_engine.director import generate_3d_scenes_from_story
from apps.ai_engine.services import generate_scenes_from_story
from .models import RenderJob
from .serializers import RenderJobSerializer
from .tasks import render_project_video_task, get_media_root, get_media_url


def dispatch_render_task(job_id: str):
    """Dispatch Celery task if worker responds, else run in background thread."""
    dispatched = False
    try:
        from celery import current_app
        insp = current_app.control.inspect(timeout=0.5)
        ping = insp.ping() if insp else None
        if ping:
            render_project_video_task.delay(str(job_id))
            dispatched = True
    except Exception:
        pass

    if not dispatched:
        threading.Thread(
            target=render_project_video_task,
            args=(str(job_id),),
            daemon=True
        ).start()


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

        dispatch_render_task(str(job.id))

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


@method_decorator(csrf_exempt, name="dispatch")
class AutoStoryToVideoAPIView(APIView):
    """
    POST /api/auto-video/
    1-Click Story to Video Pipeline:
    Takes story text and creates Project, Story, Scenes, Audio narration, and triggers MP4 render.
    """
    def post(self, request):
        story_text = (request.data.get("story") or "").strip()
        if not story_text:
            return Response(
                {"error": "গল্পের টেক্সট ফাঁকা হতে পারে না (Story text cannot be empty)"},
                status=status.HTTP_400_BAD_REQUEST
            )

        title = (request.data.get("title") or "").strip()
        if not title:
            first_line = story_text.split("\n")[0].split("।")[0].strip()
            title = first_line[:50] if first_line else f"Story {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        style = request.data.get("style", "pixar_3d")
        voice = request.data.get("voice", "bn-BD-NabanitaNeural")
        mode = request.data.get("mode", "3d")

        # 1. Create Project
        project = Project.objects.create(
            title=title,
            style=style,
            language="bn",
            status="processing"
        )

        # 2. Create Story
        Story.objects.create(
            project=project,
            text=story_text
        )

        # 3. Generate Scenes
        if mode == "3d":
            scenes_data = generate_3d_scenes_from_story(story_text, style=style)
        else:
            scenes_data = generate_scenes_from_story(story_text)

        if not scenes_data or not isinstance(scenes_data, list):
            project.status = "failed"
            project.save()
            return Response(
                {"error": "Scene generation failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        with transaction.atomic():
            for idx, scene in enumerate(scenes_data, start=1):
                if "narration" in scene and isinstance(scene["narration"], dict):
                    scene["narration"]["voice_id"] = voice
                    scene["narration"]["voice"] = voice

                characters = scene.get("characters", [])
                if isinstance(characters, list):
                    scene["characters"] = list({
                        c.get("key"): c
                        for c in characters
                        if isinstance(c, dict) and c.get("key")
                    }.values())

                Scene.objects.create(
                    project=project,
                    order=idx,
                    data=scene
                )

        # 4. Create RenderJob
        job = RenderJob.objects.create(
            project=project,
            resolution="1080p",
            fps=24,
            status="QUEUED",
            progress=5
        )

        # 5. Dispatch Video Generation (audio + moviepy assembly)
        dispatch_render_task(str(job.id))

        return Response(
            {
                "project_id": project.id,
                "title": project.title,
                "scene_count": len(scenes_data),
                "job_id": str(job.id),
                "status_url": f"/api/render-jobs/{job.id}/"
            },
            status=status.HTTP_201_CREATED
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


@method_decorator(csrf_exempt, name="dispatch")
class Save3DVideoAPIView(APIView):
    """
    POST /api/save-3d-video/
    Receives recorded 3D WebGL video from the browser, converts to clean H.264 MP4 via ffmpeg,
    and returns a downloadable URL.
    """
    def post(self, request):
        video_file = request.FILES.get("video")
        project_id = request.data.get("project_id", 1)

        if not video_file:
            return Response({"error": "No video file provided"}, status=status.HTTP_400_BAD_REQUEST)

        media_root = get_media_root()
        media_url = get_media_url()
        renders_dir = media_root / "videos" / "renders"
        os.makedirs(renders_dir, exist_ok=True)

        unique_id = uuid.uuid4().hex[:8]
        temp_input = renders_dir / f"temp_{unique_id}_{video_file.name}"
        output_mp4 = renders_dir / f"3d_animated_project_{project_id}_{unique_id}.mp4"

        with open(temp_input, "wb") as f:
            for chunk in video_file.chunks():
                f.write(chunk)

        try:
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            cmd = [
                ffmpeg_exe,
                "-y",
                "-i", str(temp_input),
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "22",
                "-c:a", "aac",
                "-b:a", "192k",
                "-movflags", "+faststart",
                str(output_mp4)
            ]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

            if temp_input.exists():
                os.remove(temp_input)

            rel_url = f"{media_url.rstrip('/')}/videos/renders/{output_mp4.name}"
            return Response({
                "success": True,
                "video_url": rel_url,
                "filename": output_mp4.name
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            rel_url = f"{media_url.rstrip('/')}/videos/renders/{temp_input.name}"
            return Response({
                "success": True,
                "video_url": rel_url,
                "filename": temp_input.name,
                "warning": str(e)
            }, status=status.HTTP_200_OK)
