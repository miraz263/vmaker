from django.db import models
from apps.scenes.models import Scene


class SceneAudio(models.Model):
    """
    Stores generated speech audio, voice settings,
    and timed viseme blendshape animations for 3D character lip-sync.
    """
    scene = models.OneToOneField(
        Scene,
        on_delete=models.CASCADE,
        related_name="audio_track"
    )

    audio_file = models.FileField(upload_to="audio/narration/")
    voice = models.CharField(max_length=60, default="bn-BD-NabanitaNeural")
    duration = models.FloatField(default=0.0, help_text="Duration in seconds")
    visemes = models.JSONField(
        default=list,
        help_text="Timed visemes for 3D character mouth synchronization"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Audio Track for Scene {self.scene.order} ({self.voice})"
