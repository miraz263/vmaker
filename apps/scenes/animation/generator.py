from .normalizer import normalize_scene_for_animation


def generate_scene_animation(scene):
    """
    Convert DB Scene JSON -> Engine-ready Animation JSON
    """
    return {
        "scene_id": scene.id,
        **normalize_scene_for_animation(scene.data or {})
    }
