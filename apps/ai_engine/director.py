import os
import json
import re
import requests
from pathlib import Path
from .storyboard import attach_visual_plan, call_llm_json
from .services import StoryParser, u_normalize, normalize_text, calculate_duration, split_sentences

BASE_DIR = Path(__file__).resolve().parent

# =================================================
# 3D Cinematic Presets
# =================================================
SHOT_PRESETS = {
    "wide": {
        "type": "wide_establishing",
        "position": {"x": 0, "y": 2.2, "z": 5.5},
        "target": {"x": 0, "y": 1.0, "z": 0},
        "fov": 50,
        "motion": "static"
    },
    "medium": {
        "type": "medium_shot",
        "position": {"x": 0, "y": 1.6, "z": 3.8},
        "target": {"x": 0, "y": 1.2, "z": 0},
        "fov": 45,
        "motion": "slow_dolly_in"
    },
    "close_up": {
        "type": "close_up",
        "position": {"x": 0, "y": 1.45, "z": 2.0},
        "target": {"x": 0, "y": 1.4, "z": 0},
        "fov": 35,
        "motion": "subtle_handheld"
    }
}

LIGHTING_PRESETS = {
    "morning": {
        "ambient": "#fffaed",
        "sun_intensity": 1.2,
        "sun_color": "#fff3d6",
        "shadows": True,
        "sky": "backgrounds/morning.jpg"
    },
    "sunset": {
        "ambient": "#ffe0b2",
        "sun_intensity": 1.4,
        "sun_color": "#ff7043",
        "shadows": True,
        "sky": "backgrounds/evening.jpg"
    },
    "night": {
        "ambient": "#1e293b",
        "sun_intensity": 0.3,
        "sun_color": "#90caf9",
        "shadows": False,
        "sky": "backgrounds/abstract.jpg"
    },
    "day": {
        "ambient": "#ffffff",
        "sun_intensity": 1.0,
        "sun_color": "#ffffff",
        "shadows": True,
        "sky": "backgrounds/default.jpg"
    }
}

ACTION_KEYWORDS = {
    "হাঁট": "walk",
    "দৌড়": "run",
    "খেল": "play_gesture",
    "দেখ": "look_around",
    "বল": "talk_happy",
    "কথা": "talk_happy",
    "হাস": "laugh",
    "ভাব": "think",
    "বস": "sit",
    "হাত নাড়": "wave"
}


# =================================================
# Rule-Based 3D Director (Always Reliable & Fast)
# =================================================
class RuleBased3DDirector:
    """
    Constructs high-fidelity 3D cinematographic scene directives
    using natural language heuristics for Bengali stories.
    """

    def __init__(self):
        self.parser = StoryParser()

    def detect_3d_action(self, text: str) -> str:
        for verb, action in ACTION_KEYWORDS.items():
            if verb in text:
                return action
        return "idle"

    def detect_lighting(self, text: str) -> dict:
        if any(w in text for w in ["সকাল", "ভোর", "সূর্যোদয়"]):
            return LIGHTING_PRESETS["morning"]
        elif any(w in text for w in ["সন্ধ্যা", "সূর্যাস্ত", "গোধূলি"]):
            return LIGHTING_PRESETS["sunset"]
        elif any(w in text for w in ["রাত", "অন্ধকার", "চাঁদ"]):
            return LIGHTING_PRESETS["night"]
        return LIGHTING_PRESETS["day"]

    def compose_3d_scenes(self, story_text: str, style: str = "pixar_3d") -> list[dict]:
        sentences = split_sentences(story_text)
        scenes = []

        shot_cycle = ["wide", "medium", "close_up", "medium"]

        # Determine story protagonist
        story_characters = self.parser.detect_characters(story_text)
        if not story_characters:
            for name in self.parser.detect_unknown_names(story_text):
                self.parser.auto_learn_character(name)
            story_characters = self.parser.detect_characters(story_text)

        default_protagonist = story_characters[0] if story_characters else {
            "key": "hero",
            "name": "hero",
            "asset": "characters/hero.png"
        }
        active_characters = [default_protagonist]

        for idx, sentence in enumerate(sentences, start=1):
            characters = self.parser.detect_characters(sentence)
            if not characters:
                for name in self.parser.detect_unknown_names(sentence):
                    self.parser.auto_learn_character(name)
                characters = self.parser.detect_characters(sentence)

            if characters:
                active_characters = characters
            else:
                characters = active_characters

            # Assign 3D transforms & actions
            characters_3d = []
            for i, c in enumerate(characters):
                pos_x = 0.0 if len(characters) == 1 else (-1.2 if i == 0 else 1.2)
                action = self.detect_3d_action(sentence)
                characters_3d.append({
                    "id": f"char_{c['key']}",
                    "key": c["key"],
                    "asset": c["asset"],
                    "model_3d": f"models/characters/{c['key']}.glb",
                    "transform": {
                        "position": {"x": pos_x, "y": 0.0, "z": 0.0},
                        "rotation": {"x": 0, "y": 15 if pos_x < 0 else -15, "z": 0},
                        "scale": {"x": 1.0, "y": 1.0, "z": 1.0}
                    },
                    "action": {
                        "clip": action,
                        "loop": True,
                        "speed": 1.0
                    },
                    "emotion": {
                        "expression": c.get("emotion", "neutral"),
                        "intensity": 0.8
                    }
                })

            shot_choice = shot_cycle[(idx - 1) % len(shot_cycle)]
            camera_preset = SHOT_PRESETS[shot_choice]
            lighting_preset = self.detect_lighting(sentence)
            background = self.parser.detect_background(sentence)

            scenes.append({
                "scene_id": idx,
                "style": style,
                "background": background,
                "environment": {
                    "background": background,
                    "lighting": lighting_preset
                },
                "camera": {
                    "type": camera_preset["type"],
                    "position": camera_preset["position"],
                    "target": camera_preset["target"],
                    "fov": camera_preset["fov"],
                    "motion": camera_preset["motion"]
                },
                "characters": characters_3d,
                "narration": {
                    "text": sentence,
                    "voice": "female_child",
                    "voice_id": "bn-BD-NabanitaNeural",
                    "lang": "bn"
                },
                "duration": calculate_duration(sentence),
                "transition": "fade"
            })

        return scenes


# =================================================
# LLM 3D Director (Groq / Gemini)
# =================================================
def generate_llm_3d_scenes(story_text: str, style: str = "pixar_3d") -> list[dict] | None:
    """
    Invoke Groq or Gemini API with structured JSON schema for 3D cinematography.
    Falls back to RuleBased3DDirector if API key is not present or API fails.
    """
    groq_api_key = os.getenv("GROQ_API_KEY")
    gemini_api_key = os.getenv("GEMINI_API_KEY")

    if not groq_api_key and not gemini_api_key:
        return None

    system_prompt = f"""You are a master 3D Animation Film Director (Pixar/Disney style).
Given a Bengali story, decompose it into sequential 3D cinematic scenes formatted strictly as JSON.
Style: {style}.
Language: Bengali (bn).

Output JSON schema:
{{
  "scenes": [
    {{
      "scene_id": 1,
      "camera": {{
        "type": "wide_establishing | medium_shot | close_up",
        "position": {{"x": 0.0, "y": 1.6, "z": 3.8}},
        "target": {{"x": 0.0, "y": 1.2, "z": 0.0}},
        "fov": 45,
        "motion": "slow_dolly_in | static | orbit"
      }},
      "environment": {{
        "preset": "morning_village | sunset_meadow | cozy_room",
        "lighting": {{"ambient": "#ffffff", "sun_intensity": 1.2, "shadows": true}}
      }},
      "characters": [
        {{
          "key": "character_name",
          "transform": {{"position": {{"x": 0, "y": 0, "z": 0}}, "rotation": {{"x": 0, "y": 0, "z": 0}}}},
          "action": {{"clip": "walk | talk_happy | idle | look_around", "loop": true}},
          "emotion": {{"expression": "happy | curious | surprised", "intensity": 0.8}}
        }}
      ],
      "narration": {{
        "text": "sentence in Bengali",
        "voice_id": "bn-BD-NabanitaNeural",
        "lang": "bn"
      }},
      "duration": 8
    }}
  ]
}}
Only return valid, raw JSON."""

    parsed = call_llm_json(system_prompt, story_text)
    if parsed and isinstance(parsed.get("scenes"), list) and parsed["scenes"]:
        return parsed["scenes"]
    print("LLM 3D Director unavailable, falling back to rule-based")
    return None


# =================================================
# Master 3D Scene Generation Entrypoint
# =================================================
def generate_3d_scenes_from_story(story_text: str, style: str = "pixar_3d") -> list[dict]:
    """
    Main director entrypoint.
    Uses LLM 3D Director when API keys are available, otherwise uses RuleBased3DDirector.
    """
    scenes = generate_llm_3d_scenes(story_text, style=style)
    if not scenes:
        scenes = RuleBased3DDirector().compose_3d_scenes(story_text, style=style)

    try:
        attach_visual_plan(story_text, scenes)
    except Exception as e:
        print(f"Storyboard planning failed, renderer will use narration text: {e}")
    return scenes
