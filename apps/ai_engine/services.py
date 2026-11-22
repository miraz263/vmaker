import re
import unicodedata
from pathlib import Path
from dataclasses import dataclass

BASE_DIR = Path(__file__).resolve().parent
MEDIA_DIR = BASE_DIR.parent.parent / "media"


# =================================================
# Unicode Normalizer
# =================================================
def u_normalize(text: str) -> str:
    if not isinstance(text, str):
        return ""
    return unicodedata.normalize("NFKC", text)


# =================================================
# Keyword Rule Data Structure
# =================================================
@dataclass
class KeywordRule:
    key: str
    value: str
    priority: int


# =================================================
# Keyword Loader (DEDUP SAFE)
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


# Pre-load shared global keyword rules
CHARACTER_KEYWORDS = load_keywords(BASE_DIR / "keywords" / "characters.txt")
BACKGROUND_KEYWORDS = load_keywords(BASE_DIR / "keywords" / "backgrounds.txt")


# =================================================
# Dynamic Asset Resolution (Prevents 404s)
# =================================================
def resolve_character_asset(key: str) -> str:
    char_dir = MEDIA_DIR / "characters"
    if char_dir.exists():
        for ext in [".png", ".jpg", ".jpeg", ".webp", ".glb"]:
            if (char_dir / f"{key}{ext}").exists():
                return f"characters/{key}{ext}"

    # Auto-fetch character sprite from web if missing
    try:
        from .web_assets import fetch_web_character
        return fetch_web_character(key)
    except Exception:
        pass

    return f"characters/{key}.png"


def resolve_background_asset(key: str) -> str:
    bg_dir = MEDIA_DIR / "backgrounds"
    if bg_dir.exists():
        for ext in [".jpg", ".jpeg", ".png", ".webp", ".glb"]:
            if (bg_dir / f"{key}{ext}").exists():
                return f"backgrounds/{key}{ext}"

    # Auto-fetch from web if missing
    try:
        from .web_assets import fetch_web_background
        return fetch_web_background(key)
    except Exception as e:
        pass

    return f"backgrounds/{key}.jpg"


# =================================================
# Text Helpers
# =================================================
def normalize_text(text: str) -> str:
    suffixes = ["দের", "গুলো", "গুলি", "কে", "তে", "য়", "টা", "টি"]
    for s in suffixes:
        text = re.sub(rf"{s}\b", "", text)
    return text


def calculate_duration(text: str) -> int:
    return max(8, min(20, len(text.split())))


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"[।!?]", text) if s.strip()]


# =================================================
# Stateless Story Parser (Thread-Safe)
# =================================================
class StoryParser:
    """
    Thread-safe story-to-scene parser.
    Instance variables prevent cross-request memory corruption.
    """

    def __init__(self, character_rules=None, background_rules=None):
        self.primary_character = None
        self.character_rules = character_rules if character_rules is not None else list(CHARACTER_KEYWORDS)
        self.background_rules = background_rules if background_rules is not None else list(BACKGROUND_KEYWORDS)
        self.known_characters = {u_normalize(r.key) for r in self.character_rules}

    def detect_background(self, text: str) -> dict:
        clean = normalize_text(text)

        for rule in self.background_rules:
            if rule.key in clean:
                return {
                    "key": rule.value,
                    "type": "image",
                    "asset": resolve_background_asset(rule.value)
                }

        if any(w in text for w in ["মন", "জীবন", "আনন্দ", "ক্লান্তি"]):
            return {
                "key": "abstract",
                "type": "image",
                "asset": resolve_background_asset("abstract")
            }

        return {
            "key": "default",
            "type": "image",
            "asset": resolve_background_asset("default")
        }

    def detect_characters(self, text: str) -> list[dict]:
        text_norm = u_normalize(text)
        clean = u_normalize(normalize_text(text_norm))

        words = [
            u_normalize(w.strip("।,!?"))
            for w in clean.split()
            if w.strip("।,!?")
        ]

        found = []

        # 1. Explicit character keyword matching
        for rule in self.character_rules:
            if u_normalize(rule.key) in words:
                found.append(rule.value)

        if found:
            if self.primary_character is None:
                self.primary_character = found[0]

            unique = list(dict.fromkeys(found))
            return [{
                "key": c,
                "emotion": "neutral",
                "position": "center",
                "asset": resolve_character_asset(c)
            } for c in unique]

        # 2. Pronoun resolution back to primary character
        if any(p in text_norm for p in ["সে", "তার", "তাকে", "ভাবল"]):
            if self.primary_character:
                return [{
                    "key": self.primary_character,
                    "emotion": "neutral",
                    "position": "center",
                    "asset": resolve_character_asset(self.primary_character)
                }]

        return []

    def detect_unknown_names(self, text: str) -> list[str]:
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
            if clean in self.known_characters or clean in blacklist:
                continue
            if len(clean) < 3 or len(clean) > 6:
                continue
            if any(v in text for v in verbs):
                found.append(clean)

        return found

    def auto_learn_character(self, name: str):
        name = u_normalize(name)
        if name in self.known_characters or len(name) < 3 or len(name) > 6:
            return

        file_path = BASE_DIR / "keywords" / "characters.txt"
        try:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(f"\n{name} = {name.lower()} | 80")
        except Exception:
            pass

        rule = KeywordRule(key=name, value=name.lower(), priority=80)
        self.character_rules.append(rule)
        self.known_characters.add(name)

    def parse(self, story_text: str) -> list[dict]:
        self.primary_character = None
        scenes = []

        for idx, sentence in enumerate(split_sentences(story_text), start=1):
            characters = self.detect_characters(sentence)

            if not characters:
                for name in self.detect_unknown_names(sentence):
                    self.auto_learn_character(name)
                characters = self.detect_characters(sentence)

            scenes.append({
                "scene_id": idx,
                "background": self.detect_background(sentence),
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


# =================================================
# Public API Function (Backward Compatible)
# =================================================
def generate_scenes_from_story(story_text: str) -> list[dict]:
    """Thread-safe entrypoint for generating scenes from story text."""
    parser = StoryParser()
    return parser.parse(story_text)
