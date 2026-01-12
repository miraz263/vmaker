from django.db import models
from apps.projects.models import Project


class Scene(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="scenes"
    )

    order = models.PositiveIntegerField(
        default=0,
        help_text="Scene order in timeline"
    )

    data = models.JSONField(
        help_text="Generated scene data (background, characters, narration, duration)"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "created_at"]

    def __str__(self):
        return f"Scene {self.order} for {self.project.title}"
