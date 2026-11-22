def normalize_scene_for_animation(data: dict) -> dict:
    """
    Convert DB Scene JSON -> Engine-ready 3D Animation JSON
    Includes timed visemes for 3D character lip-sync and audio playback.
    """

    # ------------------
    # Background / Environment
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
                "position": {"x": x, "y": 75, "z": 0},
                "pose": "idle",
                "emotion": c.get("emotion", "neutral"),
                "facing": "right"
            },
            "actions": []
        })

    # ------------------
    # Narration & 3D Lip-Sync Audio
    # ------------------
    narration = data.get("narration", {})
    audio_data = data.get("audio", {})

    narration_block = {
        "text": narration.get("text", ""),
        "voice": {
            "lang": narration.get("lang", "bn"),
            "voice_id": audio_data.get("voice", narration.get("voice_id", "bn-BD-NabanitaNeural")),
            "gender": narration.get("voice", "female_child")
        },
        "audio_url": audio_data.get("url") or narration.get("audio_url", ""),
        "visemes": audio_data.get("visemes") or narration.get("visemes", []),
        "start_at": narration.get("start_at", 0.5)
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
            "zoom": 1.0,
            "position": {"x": 0, "y": 1.5, "z": 4.0}
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
