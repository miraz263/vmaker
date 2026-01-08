from django.db import models
from apps.projects.models import Project


class Story(models.Model):
    project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        related_name='story'
    )
    text = models.TextField()

    def __str__(self):
        return f"Story for {self.project.title}"
