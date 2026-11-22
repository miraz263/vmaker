import uuid
from django.db import models
from apps.projects.models import Project


class RenderJob(models.Model):
    """
    Tracks asynchronous video rendering jobs, progress percentage, and output files.
    """
    STATUS_CHOICES = [
        ("QUEUED", "Queued in Task Engine"),
        ("AUDIO_GENERATING", "Generating Voice Narration & Audio"),
        ("SCENE_COMPILING", "Compiling 3D Scene Frames & Visuals"),
        ("ENCODING", "Encoding Final MP4 Video"),
        ("COMPLETED", "Video Rendering Complete"),
        ("FAILED", "Rendering Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="render_jobs"
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="QUEUED"
    )
    progress = models.PositiveSmallIntegerField(
        default=0,
        help_text="Rendering progress (0% - 100%)"
    )

    resolution = models.CharField(max_length=20, default="1080p")
    fps = models.PositiveSmallIntegerField(default=24)

    output_file = models.FileField(
        upload_to="videos/renders/",
        blank=True,
        null=True
    )
    video_url = models.CharField(max_length=500, blank=True)

    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"RenderJob {self.id} [{self.status} {self.progress}%] for {self.project.title}"
