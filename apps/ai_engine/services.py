import re
from pathlib import Path
from dataclasses import dataclass


# =================================================
# Keyword rule structure
# =================================================
@dataclass
class KeywordRule:
    key: str
    value: str
    priority: int


# =================================================
# Keyword loader
# =================================================
def load_keywords(file_path):
    rules = []
    path = Path(file_path)

    if not path.exists():
        return rules

    default_priority = 1000

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line or line.startswith("#") or "=" not in line:
                continue

            left, right = line.split("=", 1)
            key = left.strip()

            if "|" in right:
                value, pr = right.split("|", 1)
                value = value.strip()
                try:
                    priority = int(pr.strip())
                except ValueError:
                    priority = default_priority
            else:
                value = right.strip()
                priority = default_priority

            rules.append(KeywordRule(key, value, priority))
            default_priority -= 1

    rules.sort(key=lambda r: r.priority, reverse=True)
    return rules


# =================================================
# Load keyword files
# =================================================
BASE_DIR = Path(__file__).resolve().parent

BACKGROUND_KEYWORDS = load_keywords(BASE_DIR / "keywords" / "backgrounds.txt")
CHARACTER_KEYWORDS = load_keywords(BASE_DIR / "keywords" / "characters.txt")

KNOWN_CHARACTERS = set(r.key for r in CHARACTER_KEYWORDS)


# =================================================
# Helpers
# =================================================
def normalize_text(text):
    suffixes = ["দের", "গুলো", "গুলি", "কে", "তে", "য়", "টা", "টি"]
    for s in suffixes:
        text = re.sub(rf"{s}\b", "", text)
    return text


# =================================================
# Auto-learn (STRICT)
# =================================================
def auto_learn_character(name):
    if name in KNOWN_CHARACTERS:
        return

    if len(name) < 3 or len(name) > 6:
        return

    file_path = BASE_DIR / "keywords" / "characters.txt"

    with open(file_path, "a", encoding="utf-8") as f:
        f.write(f"\n{name} = {name.lower()} | 80")

    CHARACTER_KEYWORDS.append(
        KeywordRule(key=name, value=name.lower(), priority=80)
    )
    KNOWN_CHARACTERS.add(name)


def detect_unknown_names(text):
    words = text.split()

    blacklist = {
        "একদিন", "হঠাৎ", "কখনো", "তখন", "যেন", "আরও",
        "মন", "জীবন", "আনন্দ", "ক্লান্তি", "নীরবতা",
        "শব্দ", "আলো", "ছায়া", "মুহূর্ত", "চারপাশ",
        "উঠে", "উঠতে", "আছে", "পরে", "আগে"
    }

    verbs = ["দেখ", "বস", "দাঁড়", "হাঁট", "বুঝ", "চিন", "কর", "নিল", "দিল"]

    for w in words:
        clean = normalize_text(w)

        if not re.fullmatch(r"[অ-হ]+", clean):
            continue

        if clean in blacklist or clean in KNOWN_CHARACTERS:
            continue

        if len(clean) < 3 or len(clean) > 6:
            continue

        if any(v in text for v in verbs):
            return [clean]

    return []


# =================================================
# Story memory
# =================================================
PRIMARY_CHARACTER = None


# =================================================
# Detection logic (UPDATED)
# =================================================
def detect_background(text):
    clean = normalize_text(text)

    for rule in BACKGROUND_KEYWORDS:
        if rule.key in clean:
            return {
                "key": rule.value,
                "type": "image",
                "asset": f"backgrounds/{rule.value}.jpg"
            }

    if any(w in text for w in ["মন", "জীবন", "আনন্দ", "ক্লান্তি"]):
        return {
            "key": "abstract",
            "type": "image",
            "asset": "backgrounds/abstract.jpg"
        }

    return {
        "key": "default",
        "type": "image",
        "asset": "backgrounds/default.jpg"
    }


def detect_characters(text):
    global PRIMARY_CHARACTER

    clean = normalize_text(text)
    found = []

    for rule in CHARACTER_KEYWORDS:
        if rule.key in clean:
            found.append(rule.value)

    if found:
        if PRIMARY_CHARACTER is None:
            PRIMARY_CHARACTER = found[0]

        return [
            {
                "key": c,
                "emotion": "neutral",
                "position": "center",
                "asset": f"characters/{c}.png"
            }
            for c in set(found)
        ]

    if any(p in text for p in ["সে", "তার", "তাকে", "বুঝল"]):
        if PRIMARY_CHARACTER:
            return [{
                "key": PRIMARY_CHARACTER,
                "emotion": "neutral",
                "position": "center",
                "asset": f"characters/{PRIMARY_CHARACTER}.png"
            }]

    return []


def calculate_duration(text):
    return max(8, min(20, len(text.split())))


def split_sentences(text):
    return [s.strip() for s in re.split(r"[।!?]", text) if s.strip()]


# =================================================
# MAIN GENERATOR (UPDATED OUTPUT)
# =================================================
def generate_scenes_from_story(story_text):
    global PRIMARY_CHARACTER

    PRIMARY_CHARACTER = None
    scenes = []

    for idx, sentence in enumerate(split_sentences(story_text), start=1):

        for name in detect_unknown_names(sentence):
            auto_learn_character(name)

        scenes.append({
            "scene_id": idx,
            "background": detect_background(sentence),
            "characters": detect_characters(sentence),
            "narration": {
                "text": sentence,
                "voice": "female_child",
                "lang": "bn"
            },
            "duration": calculate_duration(sentence),
            "transition": "fade"
        })

    return scenes
