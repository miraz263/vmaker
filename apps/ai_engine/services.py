import re
from pathlib import Path
from dataclasses import dataclass
import unicodedata

# =================================================
# Unicode normalize
# =================================================
def u_normalize(text: str) -> str:
    if not isinstance(text, str):
        return ""
    return unicodedata.normalize("NFKC", text)


# =================================================
# Keyword rule structure
# =================================================
@dataclass
class KeywordRule:
    key: str
    value: str
    priority: int


# =================================================
# Keyword loader (DEDUP SAFE)
# =================================================
def load_keywords(file_path):
    rules_map = {}

    path = Path(file_path)
    if not path.exists():
        return []

    priority_counter = 1000

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line or line.startswith("#") or "=" not in line:
                continue

            left, right = line.split("=", 1)
            key = u_normalize(left.strip())

            if "|" in right:
                value_part, priority_part = right.split("|", 1)
                value = value_part.strip()
                try:
                    priority = int(priority_part.strip())
                except ValueError:
                    priority = priority_counter
            else:
                value = right.strip()
                priority = priority_counter

            if key not in rules_map or priority > rules_map[key].priority:
                rules_map[key] = KeywordRule(key, value, priority)

            priority_counter -= 1

    rules = list(rules_map.values())
    rules.sort(key=lambda r: r.priority, reverse=True)
    return rules


# =================================================
# Load keyword files
# =================================================
BASE_DIR = Path(__file__).resolve().parent

CHARACTER_KEYWORDS = load_keywords(BASE_DIR / "keywords" / "characters.txt")
BACKGROUND_KEYWORDS = load_keywords(BASE_DIR / "keywords" / "backgrounds.txt")

KNOWN_CHARACTERS = {u_normalize(r.key) for r in CHARACTER_KEYWORDS}


# =================================================
# Helpers
# =================================================
def normalize_text(text):
    suffixes = ["দের", "গুলো", "গুলি", "কে", "তে", "য়", "টা", "টি"]
    for s in suffixes:
        text = re.sub(rf"{s}\b", "", text)
    return text


# =================================================
# Auto-learn (SAFE)
# =================================================
def auto_learn_character(name):
    name = u_normalize(name)

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


# =================================================
# Unknown name detector (STRICT)
# =================================================
def detect_unknown_names(text):
    words = text.split()

    blacklist = {
        "একদিন", "হঠাৎ", "কখনো", "তখন", "যেন", "আরও",
        "মন", "জীবন", "আনন্দ", "ক্লান্তি", "নীরবতা",
        "শব্দ", "আলো", "ছায়া", "মুহূর্ত", "চারপাশ",
        "নরম", "ছোট", "বড়", "ভালো", "মন্দ",
        "অন্ধকার", "ধীরে"
    }

    verbs = ["দেখ", "বস", "দাঁড়", "হাঁট", "বুঝ", "চিন", "কর", "নিল", "দিল"]

    found = []

    for w in words:
        clean = u_normalize(normalize_text(w))

        if not re.fullmatch(r"[অ-হ]+", clean):
            continue

        if clean in KNOWN_CHARACTERS or clean in blacklist:
            continue

        if len(clean) < 3 or len(clean) > 6:
            continue

        if any(v in text for v in verbs):
            found.append(clean)

    return found


# =================================================
# Story memory
# =================================================
PRIMARY_CHARACTER = None


# =================================================
# Background detection
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


# =================================================
# Character detection (FINAL & CLEAN)
# =================================================
def detect_characters(text):
    global PRIMARY_CHARACTER

    text = u_normalize(text)
    clean = u_normalize(normalize_text(text))

    words = [
        u_normalize(w.strip("।,!?"))
        for w in clean.split()
        if w.strip("।,!?")
    ]

    found = []

    # 1️⃣ Explicit character match
    for rule in CHARACTER_KEYWORDS:
        if u_normalize(rule.key) in words:
            found.append(rule.value)

    if found:
        if PRIMARY_CHARACTER is None:
            PRIMARY_CHARACTER = found[0]

        unique = list(dict.fromkeys(found))

        return [{
            "key": c,
            "emotion": "neutral",
            "position": "center",
            "asset": f"characters/{c}.png"
        } for c in unique]

    # 2️⃣ Pronoun fallback
    if any(p in text for p in ["সে", "তার", "তাকে", "ভাবল"]):
        if PRIMARY_CHARACTER:
            return [{
                "key": PRIMARY_CHARACTER,
                "emotion": "neutral",
                "position": "center",
                "asset": f"characters/{PRIMARY_CHARACTER}.png"
            }]

    return []


# =================================================
# Duration + sentence split
# =================================================
def calculate_duration(text):
    return max(8, min(20, len(text.split())))


def split_sentences(text):
    return [s.strip() for s in re.split(r"[।!?]", text) if s.strip()]


# =================================================
# MAIN GENERATOR (ORDER SAFE)
# =================================================
def generate_scenes_from_story(story_text):
    global PRIMARY_CHARACTER

    PRIMARY_CHARACTER = None
    scenes = []

    for idx, sentence in enumerate(split_sentences(story_text), start=1):

        characters = detect_characters(sentence)

        if not characters:
            for name in detect_unknown_names(sentence):
                auto_learn_character(name)
            characters = detect_characters(sentence)

        scenes.append({
            "scene_id": idx,
            "background": detect_background(sentence),
            "characters": characters,
            "narration": {
                "text": sentence,
                "voice": "female_child",
                "lang": "bn"
            },
            "duration": calculate_duration(sentence),
            "transition": "fade"
        })

    return scenes
