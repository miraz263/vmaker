from django.db import models


# =================================================
# Legacy 2D Assets (Maintained for Backward Compatibility)
# =================================================
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


# =================================================
# Modern 3D Assets (Sprint 3: GLTF/GLB & Animations)
# =================================================
class Asset3D(models.Model):
    """
    3D Models (Characters, Environments, Props) stored as .glb / .gltf
    """
    CATEGORY_CHOICES = [
        ("character", "3D Character Avatar"),
        ("environment", "3D Scene Environment"),
        ("prop", "3D Prop / Object"),
    ]

    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default="character"
    )
    file = models.FileField(upload_to="models/3d/")
    thumbnail = models.ImageField(upload_to="models/thumbnails/", blank=True, null=True)
    has_visemes = models.BooleanField(
        default=True,
        help_text="Supports mouth blendshapes for audio lip-sync"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Default scale, camera offset, animations list"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.get_category_display()}] {self.name}"


class AnimationClip(models.Model):
    """
    Skeletal animation clips (.glb) for retargeting to 3D characters
    """
    name = models.CharField(max_length=100, unique=True) # e.g. "idle", "walk", "talk_happy"
    clip_file = models.FileField(upload_to="models/animations/")
    duration = models.FloatField(default=1.0)
    loop = models.BooleanField(default=True)

    def __str__(self):
        return f"Animation: {self.name} ({self.duration}s)"
