def generate_scene_animation(scene):
    """
    Convert Scene.data (JSON) → Animation JSON (SAFE)
    """

    data = scene.data or {}

    # -----------------------
    # Background
    # -----------------------
    bg = data.get("background", {})
    background = {
        "type": "image",
        "key": bg.get("key", "default"),
        "asset": bg.get("asset", "backgrounds/default.jpg"),
    }

    # -----------------------
    # Characters
    # -----------------------
    characters = []
    for c in data.get("characters", []):
        characters.append({
            "key": c.get("key"),
            "asset": c.get("asset"),
            "position": c.get("position", "center"),
            "emotion": c.get("emotion", "neutral"),
            "actions": []
        })

    # -----------------------
    # Narration
    # -----------------------
    narration = data.get("narration", {})
    narration_block = {
        "text": narration.get("text", ""),
        "voice": {
            "lang": narration.get("lang", "bn"),
            "gender": narration.get("voice", "female_child")
        },
        "start_at": 0.5
    }

    # -----------------------
    # Final Animation JSON
    # -----------------------
    return {
        "scene_id": scene.id,
        "timeline": {
            "start": 0,
            "duration": data.get("duration", 8)
        },
        "environment": {
            "background": background
        },
        "camera": {
            "type": "static",
            "zoom": 1.0
        },
        "characters": characters,
        "narration": narration_block,
        "transition": {
            "out": {
                "type": data.get("transition", "fade"),
                "duration": 0.8
            }
        }
    }
from .normalizer import normalize_scene_for_animation

def generate_scene_animation(scene):
    return {
        "scene_id": scene.id,
        **normalize_scene_for_animation(scene.data)
    }
