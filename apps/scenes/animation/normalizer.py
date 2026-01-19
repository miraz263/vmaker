def normalize_scene_for_animation(data: dict) -> dict:
    """
    Convert DB Scene JSON → Engine-ready Animation JSON
    """

    # ------------------
    # Background
    # ------------------
    bg = data.get("background", {})
    background = {
        "type": "image",
        "key": bg.get("key", "default"),
        "asset": bg.get("asset", "backgrounds/default.jpg")
    }

    # ------------------
    # Characters
    # ------------------
    characters = []

    for c in data.get("characters", []):
        pos = c.get("position", "center")

        # string → x,y
        x = 50
        if pos == "left":
            x = 30
        elif pos == "right":
            x = 70

        characters.append({
            "id": f"char_{c.get('key')}",
            "key": c.get("key"),
            "asset": c.get("asset"),
            "initial_state": {
                "position": {"x": x, "y": 75},
                "pose": "idle",
                "emotion": c.get("emotion", "neutral"),
                "facing": "right"
            },
            "actions": []
        })

    # ------------------
    # Narration
    # ------------------
    narration = data.get("narration", {})
    narration_block = {
        "text": narration.get("text", ""),
        "voice": {
            "lang": narration.get("lang", "bn"),
            "gender": narration.get("voice", "female_child")
        },
        "start_at": 0.5
    }

    # ------------------
    # Final Animation JSON
    # ------------------
    return {
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
