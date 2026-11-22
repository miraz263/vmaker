import os
import re
import asyncio
from pathlib import Path
from django.conf import settings

BENGALI_VOICES = {
    "bn-BD-NabanitaNeural": {"name": "Nabanita", "gender": "female", "region": "Bangladesh"},
    "bn-BD-PradeepNeural": {"name": "Pradeep", "gender": "male", "region": "Bangladesh"},
    "bn-IN-TanishaaNeural": {"name": "Tanishaa", "gender": "female", "region": "India"},
    "bn-IN-BashkarNeural": {"name": "Bashkar", "gender": "male", "region": "India"},
}

DEFAULT_VOICE = "bn-BD-NabanitaNeural"

# Standard blendshape presets for 3D character lip-sync
VISEME_BLENDSHAPES = {
    "viseme_sil": {"jawOpen": 0.0, "mouthClose": 1.0, "mouthSmile": 0.0, "mouthPucker": 0.0},
    "viseme_aa":  {"jawOpen": 0.75, "mouthClose": 0.0, "mouthSmile": 0.1, "mouthPucker": 0.0},
    "viseme_ee":  {"jawOpen": 0.35, "mouthClose": 0.0, "mouthSmile": 0.7, "mouthPucker": 0.0},
    "viseme_oh":  {"jawOpen": 0.55, "mouthClose": 0.0, "mouthSmile": 0.0, "mouthPucker": 0.8},
    "viseme_mbp": {"jawOpen": 0.05, "mouthClose": 0.95, "mouthSmile": 0.0, "mouthPucker": 0.0},
    "viseme_td":  {"jawOpen": 0.25, "mouthClose": 0.0, "mouthSmile": 0.2, "mouthPucker": 0.0},
    "viseme_kg":  {"jawOpen": 0.35, "mouthClose": 0.0, "mouthSmile": 0.1, "mouthPucker": 0.0},
}


def classify_bengali_char(char: str) -> str:
    """Map Bengali character / diacritic to 3D facial viseme."""
    if char in "আঅা":
        return "viseme_aa"
    elif char in "ইঈএঐিীেৈ":
        return "viseme_ee"
    elif char in "উঊওঔুূোৌ":
        return "viseme_oh"
    elif char in "পফবভম":
        return "viseme_mbp"
    elif char in "তথদধনটঠডঢণলসশরঢ়ড়":
        return "viseme_td"
    elif char in "কখগঘঙহ":
        return "viseme_kg"
    return "viseme_sil"


def generate_bengali_visemes(text: str, total_duration: float) -> list[dict]:
    """
    Generate timed 3D viseme keyframes from Bengali text and duration.
    Produces a continuous timeline of mouth shapes and blendshape weights.
    """
    words = [w.strip() for w in text.split() if w.strip()]
    if not words or total_duration <= 0:
        return [{"time": 0.0, "duration": max(1.0, total_duration), "viseme": "viseme_sil", "blendshapes": VISEME_BLENDSHAPES["viseme_sil"]}]

    lead_in = 0.2
    lead_out = 0.2
    speech_duration = max(0.5, total_duration - lead_in - lead_out)

    visemes = []
    # Start with silence
    visemes.append({
        "time": 0.0,
        "duration": lead_in,
        "viseme": "viseme_sil",
        "blendshapes": VISEME_BLENDSHAPES["viseme_sil"]
    })

    # Tokenize characters
    chars = [c for c in text if not c.isspace() and c not in "।,!?\r\n"]
    if not chars:
        chars = ["আ"]

    time_per_char = speech_duration / len(chars)
    current_time = lead_in

    prev_viseme = None
    for c in chars:
        v = classify_bengali_char(c)
        # Smooth duplicate consecutive visemes slightly
        dur = round(time_per_char, 3)
        visemes.append({
            "time": round(current_time, 3),
            "duration": dur,
            "viseme": v,
            "blendshapes": VISEME_BLENDSHAPES.get(v, VISEME_BLENDSHAPES["viseme_sil"])
        })
        current_time += dur
        prev_viseme = v

    # End with rest/silence
    visemes.append({
        "time": round(current_time, 3),
        "duration": lead_out,
        "viseme": "viseme_sil",
        "blendshapes": VISEME_BLENDSHAPES["viseme_sil"]
    })

    return visemes


def generate_bengali_tts(text: str, voice: str, output_path: str) -> float:
    """
    Generate audio narration using edge-tts.
    Returns the duration of the audio in seconds.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        import edge_tts

        async def _synthesize():
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)

        asyncio.run(_synthesize())

        # Determine audio duration via mutagen or fallback calculation
        try:
            from moviepy.editor import AudioFileClip
            with AudioFileClip(output_path) as audio:
                return round(audio.duration, 2)
        except Exception:
            # Fallback estimation based on word count
            words = len(text.split())
            return max(3.0, round(words * 0.45, 2))

    except ImportError:
        # edge-tts is not installed; write a dummy silent placeholder for local dev/testing
        with open(output_path, "wb") as f:
            f.write(b"ID3\x04\x00\x00\x00\x00\x00\x00")
        words = len(text.split())
        return max(3.0, round(words * 0.45, 2))


def create_scene_audio(scene, voice: str = DEFAULT_VOICE) -> dict:
    """
    Generate speech audio and lip-sync visemes for a Scene instance.
    Updates the SceneAudio model and scene.data JSON.
    """
    from .models import SceneAudio

    data = scene.data or {}
    narration = data.get("narration", {})
    text = narration.get("text", "").strip()

    if not text:
        text = f"Scene {scene.order}"

    voice_id = voice if voice in BENGALI_VOICES else DEFAULT_VOICE

    # Output file path
    rel_path = f"audio/narration/scene_{scene.id}_{voice_id}.mp3"
    abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)

    # 1. Generate Audio TTS
    duration = generate_bengali_tts(text, voice_id, abs_path)

    # 2. Generate 3D Lip-Sync Visemes
    visemes = generate_bengali_visemes(text, duration)

    # 3. Save or update SceneAudio model
    audio_obj, _ = SceneAudio.objects.update_or_create(
        scene=scene,
        defaults={
            "audio_file": rel_path,
            "voice": voice_id,
            "duration": duration,
            "visemes": visemes
        }
    )

    # 4. Synchronize into scene.data
    media_url = settings.MEDIA_URL.rstrip('/') + '/' + rel_path.lstrip('/')
    data["audio"] = {
        "url": media_url,
        "voice": voice_id,
        "duration": duration,
        "visemes": visemes
    }
    # Update duration if audio is longer than default
    if duration > data.get("duration", 0):
        data["duration"] = round(duration + 1.0, 1)

    scene.data = data
    scene.save(update_fields=["data"])

    return {
        "id": audio_obj.id,
        "scene_id": scene.id,
        "audio_url": media_url,
        "voice": voice_id,
        "duration": duration,
        "viseme_count": len(visemes),
        "visemes": visemes
    }
