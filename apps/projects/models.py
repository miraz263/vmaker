from django.db import models


class Project(models.Model):
    title = models.CharField(max_length=255)
    style = models.CharField(max_length=50, default='2d_cute')
    language = models.CharField(max_length=10, default='bn')
    status = models.CharField(max_length=50, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
