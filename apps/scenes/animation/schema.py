def build_character_block(character):
    return {
        "id": f"char_{character.key}",
        "key": character.key,
        "asset": character.asset,
        "layer": 2,
        "initial_state": {
            "position": character.position or {"x": 50, "y": 70},
            "scale": 1.0,
            "rotation": 0,
            "pose": character.default_pose or "idle",
            "emotion": "neutral",
            "facing": "right",
            "opacity": 1
        },
        "actions": character.actions or []
    }


def build_background_block(background):
    return {
        "type": "image",
        "key": background.key,
        "asset": background.asset,
        "parallax": 0.2,
        "lighting": background.lighting or "day"
    }
