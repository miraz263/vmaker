from django.db import models
from apps.projects.models import Project


class Scene(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='scenes'
    )
    data = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Scene for {self.project.title}"
