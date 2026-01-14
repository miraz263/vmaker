from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils.text import slugify

from apps.stories.models import Story
from apps.scenes.models import Scene
from apps.ai_engine.services import generate_scenes_from_story


# ===============================
# Rule-based helpers
# ===============================

def detect_characters(narration: str):
    mapping = {
        "নীলা": "nila",
        "পাখি": "bird",
        "শিশু": "child"
    }
    return [key for bn, key in mapping.items() if bn in narration]


def detect_background(narration: str):
    if "জানালা" in narration or "ঘর" in narration:
        return "house"
    if "উঠোন" in narration or "বাগান" in narration:
        return "yard"
    if "আকাশ" in narration or "উড়ে" in narration:
        return "sky"
    return "bg"


# ===============================
# Scene normalizer
# ===============================

def normalize_scene(scene: dict) -> dict:
    raw = (
        scene.get("narration")
        or scene.get("text")
        or (scene.get("scene", {}) or {}).get("narration")
        or (scene.get("scene", {}) or {}).get("text")
        or ""
    )

    narration = raw.get("text", "") if isinstance(raw, dict) else raw if isinstance(raw, str) else ""
    narration = narration.strip()

    background = (
        scene.get("background")
        or scene.get("bg")
        or (scene.get("scene", {}) or {}).get("background")
        or "bg"
    )
    background = background if isinstance(background, str) else "bg"

    raw_chars = (
        scene.get("characters")
        or (scene.get("scene", {}) or {}).get("characters")
        or []
    )

    characters = []
    if isinstance(raw_chars, str):
        characters = [slugify(c.strip()) for c in raw_chars.split(",") if c.strip()]
    elif isinstance(raw_chars, list):
        characters = [slugify(c) for c in raw_chars if isinstance(c, str) and c.strip()]

    characters = list(dict.fromkeys(characters))

    try:
        duration = int(scene.get("duration") or scene.get("time") or 8)
        if duration <= 0:
            duration = 8
    except (TypeError, ValueError):
        duration = 8

    return {
        "background": background,
        "characters": characters,
        "narration": narration,
        "duration": duration
    }


# ===============================
# Generate Scenes API
# ===============================

@method_decorator(csrf_exempt, name="dispatch")
class GenerateScenesAPIView(APIView):
    def post(self, request, project_id):

        story_text = request.data.get("story")

        if story_text:
            source_story_text = story_text
            source_story_id = None
        else:
            story = Story.objects.filter(project_id=project_id).order_by("-id").first()
            if not story:
                return Response({"error": "No story found"}, status=404)

            source_story_text = story.text
            source_story_id = story.id

        fallback_lines = [l.strip() for l in source_story_text.splitlines() if l.strip()]

        scenes_data = generate_scenes_from_story(source_story_text)
        if not isinstance(scenes_data, list):
            scenes_data = []

        while len(scenes_data) < len(fallback_lines):
            scenes_data.append({})

        scenes_data = scenes_data[:len(fallback_lines)]

        with transaction.atomic():
            Scene.objects.filter(project_id=project_id).delete()

            saved = []
            for idx, raw_scene in enumerate(scenes_data, start=1):
                scene = normalize_scene(raw_scene or {})

                if not scene["narration"]:
                    scene["narration"] = fallback_lines[idx - 1]

                if not scene["characters"]:
                    scene["characters"] = detect_characters(scene["narration"])

                if scene["background"] == "bg":
                    scene["background"] = detect_background(scene["narration"])

                Scene.objects.create(
                    project_id=project_id,
                    order=idx,
                    data=scene
                )
                saved.append({
        "id": obj.id,
        **obj.data
    })


        return Response(
            {
                "project_id": project_id,
                "story_id": source_story_id,
                "scene_count": len(saved),
                "scenes": saved,
                "source": "request" if story_text else "database"
            },
            status=201
        )
