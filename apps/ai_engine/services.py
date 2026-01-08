import re

BACKGROUND_KEYWORDS = {
    "বাগান": "garden",
    "গাছ": "tree",
    "পেঁচা": "tree",   # ✅ NEW
    "ঘাস": "grass",
    "ঘর": "house",
    "আকাশ": "sky",
}


CHARACTER_KEYWORDS = {
    "ওয়ারিনা": "warina",
    "পেঁচা": "owl",
    "মা": "mother",
}


def detect_background(text):
    for key, bg in BACKGROUND_KEYWORDS.items():
        if key in text:
            return bg
    return "default"


def detect_characters(text):
    chars = []
    for key, char in CHARACTER_KEYWORDS.items():
        if key in text:
            chars.append(char)

    if "দেখল" in text and "warina" not in chars:
        chars.append("warina")

    return chars or ["warina"]



def calculate_duration(text):
    words = len(text.split())
    duration = max(8, min(20, words))
    return duration



def split_sentences(text):
    sentences = re.split(r"[।!?]", text)
    return [s.strip() for s in sentences if s.strip()]


def generate_scenes_from_story(story_text):
    scenes = []
    sentences = split_sentences(story_text)

    for sentence in sentences:
        scene = {
            "background": detect_background(sentence),
            "characters": detect_characters(sentence),
            "narration": sentence,
            "duration": calculate_duration(sentence),
        }
        scenes.append(scene)

    return scenes
