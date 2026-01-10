from django.db import models


class Character(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class CharacterAsset(models.Model):
    character = models.ForeignKey(
        Character,
        on_delete=models.CASCADE,
        related_name="assets"
    )

    image = models.ImageField(upload_to="characters/")
    pose = models.CharField(max_length=50)  # idle, happy, running
    tags = models.CharField(
        max_length=200,
        blank=True,
        help_text="comma separated keywords"
    )

    def __str__(self):
        return f"{self.character.name} - {self.pose}"
