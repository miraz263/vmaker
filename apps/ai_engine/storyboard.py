"""
Storyboard planner: turns a story into per-scene image prompts and camera moves.

Two things keep the video looking like one film instead of random pictures:
  * a "character bible" — one fixed English description per character, repeated
    word-for-word in every scene prompt;
  * one seed per story, shared by every scene.

With GROQ_API_KEY or GEMINI_API_KEY set (both have free tiers) an LLM writes the
storyboard. Without them a keyword-based planner is used.
"""

import hashlib
import json
import logging
import os
import random
import re
import unicodedata

import requests

logger = logging.getLogger(__name__)

STYLE_PROMPT = (
    "3D animated children's movie still, cute stylized cartoon, soft warm cinematic lighting, "
    "rich colors, depth of field"
)

NEGATIVE_HINT = "no text, no watermark, no logo, no subtitles"

SHOT_PROMPTS = {
    "wide": "wide establishing shot, the whole scenery visible, character small in the frame",
    "medium": "medium shot, character from the knees up",
    "close_up": "close-up shot of the character's face and expression",
}

CAMERA_MOVES = ["push_in", "pull_out", "pan_left", "pan_right", "tilt_up"]

# Fallback character descriptions for names/animals the keyword planner can spot.
CHARACTER_HINTS = {
    "পান্ডা": "a cute baby panda with soft black-and-white fur and round ears",
    "খরগোশ": "a cute fluffy white bunny with long ears and a pink nose",
    "বিড়াল": "a cute fluffy orange kitten with green eyes",
    "কুকুর": "a cute friendly brown puppy with floppy ears",
    "হাঁস": "a cute yellow baby duckling",
    "পাখি": "a cute small blue songbird",
    "পেঁচা": "a cute round brown owl with big eyes",
    "হাতি": "a cute small grey baby elephant with big ears",
    "বানর": "a cute playful little brown monkey",
    "বাঘ": "a cute friendly tiger cub with orange stripes",
    "শিয়াল": "a cute clever little red fox",
    "শেয়াল": "a cute clever little red fox",
    # Insects & small creatures
    "পিঁপড়": "a tiny cute cartoon red ant with big round eyes, six thin legs and two curly antennae",
    "পিপড়": "a tiny cute cartoon red ant with big round eyes, six thin legs and two curly antennae",
    "পিপীলিকা": "a tiny cute cartoon red ant with big round eyes, six thin legs and two curly antennae",
    "মৌমাছি": "a cute chubby cartoon honeybee with yellow and black stripes and shiny wings",
    "প্রজাপতি": "a cute colorful cartoon butterfly with big patterned wings",
    "ফড়িং": "a cute green cartoon grasshopper with long legs",
    "মাকড়সা": "a cute friendly cartoon spider with big eyes",
    "শামুক": "a cute cartoon snail with a spiral orange shell",
    "কচ্ছপ": "a cute cartoon green turtle with a patterned shell",
    "ব্যাঙ": "a cute cartoon green frog with big round eyes",
    "ইঁদুর": "a cute little grey cartoon mouse with big round ears",
    "কাঠবিড়ালি": "a cute cartoon squirrel with a fluffy bushy tail",
    # Birds
    "কবুতর": "a cute plump cartoon grey-white pigeon with shiny green-purple neck feathers and pink feet",
    "পায়রা": "a cute plump cartoon grey-white pigeon with shiny green-purple neck feathers and pink feet",
    "ঘুঘু": "a cute soft brown cartoon dove with a spotted neck",
    "চড়ুই": "a cute tiny brown cartoon sparrow",
    "টিয়া": "a cute bright green cartoon parrot with a red beak",
    "ময়না": "a cute glossy black cartoon myna bird with a yellow beak",
    "কোকিল": "a cute dark cartoon cuckoo bird with red eyes",
    "মুরগি": "a cute plump cartoon hen with brown feathers and a red comb",
    "মোরগ": "a cute proud cartoon rooster with a red comb and colorful tail",
    "ময়ূর": "a cute cartoon peacock with a big blue-green tail",
    # More animals
    "গরু": "a cute cartoon brown-and-white calf",
    "ছাগল": "a cute little cartoon goat with tiny horns",
    "ভেড়া": "a cute fluffy white cartoon lamb",
    "ঘোড়া": "a cute cartoon brown pony with a flowing mane",
    "সিংহ": "a cute cartoon lion cub with a fluffy golden mane",
    "ভালুক": "a cute cuddly brown cartoon bear cub",
    "হরিণ": "a cute cartoon spotted baby deer",
    "জিরাফ": "a cute cartoon baby giraffe with brown spots",
    "কুমির": "a cute friendly green cartoon crocodile",
    "মাছ": "a cute colorful cartoon fish with big eyes",
    # People & roles from folk tales
    "কাঠুরে": "a poor but kind South Asian woodcutter man with a short black beard, a faded brown kurta, a lungi and a cloth tied on his head",
    "কাঠুরিয়া": "a poor but kind South Asian woodcutter man with a short black beard, a faded brown kurta, a lungi and a cloth tied on his head",
    "দেবদূত": "a glowing kind angel with white feathered wings, a flowing white robe and a soft golden halo",
    "ফেরেশতা": "a glowing kind angel with white feathered wings, a flowing white robe and a soft golden halo",
    "জলপরী": "a friendly mermaid with long dark hair and a shimmering blue-green tail",
    "পরী": "a tiny friendly fairy with sparkling wings and a pastel dress",
    "রাজকুমারী": "a young princess with long black hair, a pink gown and a small golden tiara",
    "রাজকুমার": "a young prince with a blue royal tunic and a small golden crown",
    "রাজা": "a kind old king with a grey beard, a golden crown and a red royal robe",
    "রানি": "a graceful queen with a golden crown and a purple sari",
    "রাণী": "a graceful queen with a golden crown and a purple sari",
    "কৃষক": "a cheerful South Asian farmer with a straw hat, a white vest and a lungi",
    "চাষি": "a cheerful South Asian farmer with a straw hat, a white vest and a lungi",
    "জেলে": "a South Asian fisherman with a fishing net, a checked lungi and a towel on his shoulder",
    "শিকারি": "a hunter with a bow and arrows, a green vest and a cap",
    "সাধু": "a wise old hermit with a long white beard and saffron robes",
    "বুড়ি": "a kind old village woman with white hair and a white sari",
    "বুড়ো": "a kind old village man with a white beard and a walking stick",
    "ব্যবসায়ী": "a plump merchant with a turban, a fancy vest and a money pouch",
    "শিক্ষক": "a friendly teacher with glasses, a white shirt and a book in hand",
    "ছেলে": "a cute little South Asian boy with short black hair, blue t-shirt and shorts",
    "মেয়ে": "a cute little South Asian girl with black pigtails and a yellow frock",
    "দাদা": "a kind old grandfather with white hair, glasses and a white kurta",
    "দাদি": "a kind old grandmother with grey hair in a bun and a green sari",
}

DEFAULT_HERO = "a cute little South Asian child with big brown eyes, colorful clothes and a small backpack"

# Bengali word stems → English scenery/action phrases.
SETTING_HINTS = {
    "জঙ্গল": "lush tropical jungle with giant leaves and hanging vines",
    "বন": "sunlit green forest with tall trees",
    "বাঁশ": "bamboo grove with tall green bamboo stalks",
    "নদী": "sparkling clear river with smooth stones",
    "পুকুর": "calm village pond with lotus flowers",
    "স্কুল": "colorful village school building with a playground",
    "রাস্তা": "winding dirt road through green fields",
    "পথ": "narrow forest path lined with wildflowers",
    "গ্রাম": "peaceful Bengali village with thatched huts and banana trees",
    "বাড়ি": "cozy small house with a tin roof and flower garden",
    "ঘর": "cozy room interior with wooden furniture and morning window light",
    "কুঁড়েঘর": "small bamboo hut on stilts",
    "পাহাড়": "rolling green hills and misty mountains",
    "মাঠ": "wide green meadow with wildflowers",
    "বাজার": "busy colorful village market",
    "সমুদ্র": "sunny beach with gentle waves",
    "বাগান": "flower garden with butterflies",
}

TIME_HINTS = {
    "সকাল": "early morning golden sunlight with soft mist",
    "ভোর": "dawn with pink sky and soft mist",
    "দুপুর": "bright midday sunlight",
    "বিকাল": "warm late afternoon light",
    "সন্ধ্যা": "orange sunset glow",
    "রাত": "moonlit night with glowing fireflies",
    "বৃষ্টি": "gentle rain with wet shiny leaves",
}

ACTION_HINTS = {
    "সোনার কুড়াল": "holding up a shining golden axe",
    "রুপার কুড়াল": "holding up a shining silver axe",
    "লোহার কুড়াল": "holding up an old iron axe with a wooden handle",
    "তিনটি কুড়াল": "giving golden, silver and iron axes as a gift",
    "কাঠ কাট": "chopping wood with an axe",
    "পানিতে পড়": "the axe slipping and falling into the river with a splash",
    "দুঃখ": "looking very sad",
    "আনন্দ": "smiling with joy",
    "খুশি": "looking happy",
    "উপহার": "receiving a gift",
    "জিজ্ঞেস": "asking a question kindly",
    "ঘুম": "sleeping peacefully, curled up and cozy",
    "হাঁট": "walking happily",
    "দৌড়": "running joyfully",
    "খেল": "playing happily",
    "খা": "eating with delight",
    "হাস": "laughing with a big smile",
    "কাঁদ": "crying with teary eyes",
    "ভয়": "looking scared",
    "দেখ": "looking around in wonder",
    "হাত নাড়": "waving goodbye",
    "ব্যাগ": "packing a small backpack",
    "বস": "sitting down",
    "লাফ": "jumping in excitement",
    "উড়": "flying",
    "সাঁতার": "swimming",
}


def _story_seed(story_text: str) -> int:
    if not story_text:
        return random.randint(1, 999_999)
    return int(hashlib.sha1(story_text.encode("utf-8")).hexdigest(), 16) % 1_000_000


# -------------------------------------------------
# LLM calls (Groq / Gemini free tiers)
# -------------------------------------------------
def call_llm_json(system_prompt: str, user_prompt: str, timeout: int = 40) -> dict | None:
    """Ask Groq, then Gemini, for a JSON object. Returns None if neither works."""
    groq_key = os.getenv("GROQ_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")

    if groq_key:
        try:
            res = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}"},
                json={
                    "model": os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.4,
                },
                timeout=timeout,
            )
            res.raise_for_status()
            return json.loads(res.json()["choices"][0]["message"]["content"])
        except Exception as e:
            logger.warning(f"Groq storyboard call failed: {e}")

    if gemini_key:
        try:
            model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
            res = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                headers={"x-goog-api-key": gemini_key},
                json={
                    "systemInstruction": {"parts": [{"text": system_prompt}]},
                    "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                    "generationConfig": {"responseMimeType": "application/json", "temperature": 0.4},
                },
                timeout=timeout,
            )
            res.raise_for_status()
            text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
        except Exception as e:
            logger.warning(f"Gemini storyboard call failed: {e}")

    # Keyless fallback: Pollinations' free text API (same service that draws the images).
    # Set POLLINATIONS_TEXT=0 to turn it off.
    if os.getenv("POLLINATIONS_TEXT", "1") != "0":
        try:
            headers = {"Content-Type": "application/json"}
            if os.getenv("POLLINATIONS_TOKEN"):
                headers["Authorization"] = f"Bearer {os.getenv('POLLINATIONS_TOKEN')}"
            res = requests.post(
                "https://text.pollinations.ai/openai",
                headers=headers,
                json={
                    "model": os.getenv("POLLINATIONS_TEXT_MODEL", "openai"),
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "response_format": {"type": "json_object"},
                },
                timeout=max(timeout, 90),
            )
            res.raise_for_status()
            text = res.json()["choices"][0]["message"]["content"]
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
            return json.loads(text)
        except Exception as e:
            logger.warning(f"Pollinations text storyboard call failed: {e}")

    return None


LLM_SYSTEM_PROMPT = """You are the storyboard artist for a 3D animated children's cartoon.
You get a story (usually Bengali) already split into numbered narration lines.
Plan exactly one shot per line.

Return JSON:
{
  "characters": [
    {"name": "name as in story", "look": "fixed English visual description: species/age, colors, clothes, accessories. 15-30 words."}
  ],
  "shots": [
    {
      "line": 1,
      "characters": ["names visible in this shot"],
      "setting": "English: where, time of day, weather, key props",
      "action": "English: what the characters are doing and their expression",
      "shot": "wide | medium | close_up",
      "camera": "push_in | pull_out | pan_left | pan_right | tilt_up"
    }
  ]
}
Rules:
- Characters are exactly who the story says: an ant stays an ant, a woodcutter is an adult man,
  an angel is an adult angel. Never turn a character into a child unless the story says child.
- Each "look" starts with what the character is (e.g. "a tiny red ant", "an adult South Asian
  woodcutter man"), then colors, clothes, accessories. Cartoon-cute, but true to the story.
- Keep each look identical across shots.
- In "action" refer to characters by an English noun ("the woodcutter", "the ant"), never by
  Bengali words or Bengali script.
- Vary shot sizes like a film: open with a wide shot, use close-ups for emotions.
- Settings must follow the story's continuity (same place stays the same).
- English only in descriptions. No text or signs in the image."""


def _llm_storyboard(lines: list[str]) -> dict | None:
    numbered = "\n".join(f"{i}. {line}" for i, line in enumerate(lines, start=1))
    data = call_llm_json(LLM_SYSTEM_PROMPT, numbered)
    if not data or not isinstance(data.get("shots"), list):
        return None

    bible = {
        str(c.get("name", "")).strip(): str(c.get("look", "")).strip()
        for c in data.get("characters", [])
        if isinstance(c, dict) and c.get("name") and c.get("look")
    }

    shots_by_line = {}
    for s in data["shots"]:
        if isinstance(s, dict):
            try:
                shots_by_line[int(s.get("line"))] = s
            except (TypeError, ValueError):
                continue

    shots = []
    for i in range(1, len(lines) + 1):
        s = shots_by_line.get(i, {})
        names = [n for n in s.get("characters", []) if isinstance(n, str)]
        shots.append({
            "characters": [bible[n] for n in names if n in bible] or list(bible.values())[:1],
            "setting": str(s.get("setting", "")),
            "action": str(s.get("action", "")),
            "shot": s.get("shot") if s.get("shot") in SHOT_PROMPTS else None,
            "camera": s.get("camera") if s.get("camera") in CAMERA_MOVES else None,
        })
    return {"bible": bible, "shots": shots}


# -------------------------------------------------
# Keyword fallback
# -------------------------------------------------
def _match(text: str, table: dict, limit: int) -> list[str]:
    """Matches in the order they appear in the text."""
    # য়/ড়/ঢ় can be one code point or base letter + nukta; compare in one form.
    text = unicodedata.normalize("NFC", text or "")
    hits = sorted(
        (text.find(k), desc)
        for key, desc in table.items()
        if (k := unicodedata.normalize("NFC", key)) in text
    )
    seen = []
    for _, desc in hits:
        if desc not in seen:
            seen.append(desc)
    return seen[:limit]


def _rule_storyboard(story_text: str, lines: list[str]) -> dict:
    hero_looks = _match(story_text, CHARACTER_HINTS, 2) or [DEFAULT_HERO]
    bible = {f"character_{i}": look for i, look in enumerate(hero_looks, start=1)}

    shots = []
    last_setting = "sunlit green forest with tall trees"
    last_time = "soft warm daylight"
    for line in lines:
        setting = _match(line, SETTING_HINTS, 1)
        time_of_day = _match(line, TIME_HINTS, 1)
        last_setting = setting[0] if setting else last_setting
        last_time = time_of_day[0] if time_of_day else last_time
        actions = _match(line, ACTION_HINTS, 2)
        # The hero stays in every shot ("সে" etc. usually means the hero);
        # anyone else named in this line joins them.
        line_chars = [c for c in _match(line, CHARACTER_HINTS, 2) if c != hero_looks[0]]
        shots.append({
            "characters": (hero_looks[:1] + line_chars)[:2],
            "setting": f"{last_setting}, {last_time}",
            "action": ", ".join(actions) if actions else "smiling with curious happy eyes",
            "shot": None,
            "camera": None,
        })
    return {"bible": bible, "shots": shots}


# -------------------------------------------------
# Public API
# -------------------------------------------------
def build_prompt(shot: dict) -> str:
    """Shot and setting first: image models weight the start of the prompt most."""
    chars = " and ".join(shot["characters"])
    parts = [
        SHOT_PROMPTS.get(shot["shot"], SHOT_PROMPTS["medium"]),
        f"in {shot['setting']}" if shot["setting"] else "",
        f"{chars}, {shot['action']}" if chars else shot["action"],
        STYLE_PROMPT,
        NEGATIVE_HINT,
    ]
    return ", ".join(p for p in parts if p)


def attach_visual_plan(story_text: str, scenes: list[dict]) -> list[dict]:
    """
    Add scene["visual"] = {prompt, shot, camera, seed} to every scene, in place.
    Uses each scene's narration text as its storyboard line.
    """
    lines = [
        (sc.get("narration") or {}).get("text", "") if isinstance(sc, dict) else ""
        for sc in scenes
    ]
    plan = _llm_storyboard(lines) if any(lines) else None
    source = "llm"
    if not plan:
        plan = _rule_storyboard(story_text, lines)
        source = "keywords"

    seed = _story_seed(story_text)
    default_shots = ["wide", "medium", "close_up", "medium"]

    for idx, (sc, shot) in enumerate(zip(scenes, plan["shots"])):
        shot["shot"] = shot["shot"] or default_shots[idx % len(default_shots)]
        shot["camera"] = shot["camera"] or CAMERA_MOVES[idx % len(CAMERA_MOVES)]
        sc["visual"] = {
            "prompt": build_prompt(shot),
            "shot": shot["shot"],
            "camera": shot["camera"],
            "seed": seed,
            "planner": source,
        }
    logger.info(f"Storyboard built with {source} planner for {len(scenes)} scenes")
    return scenes
