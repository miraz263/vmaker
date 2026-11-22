"""
Auto Web Asset Fetcher for vmaker
Automatically discovers, searches, and downloads Pixar/3D-style
backgrounds and character visuals from the web when not available locally.
"""

import os
import re
import urllib.request
import urllib.parse
import json
import logging
from pathlib import Path

try:
    from django.conf import settings
    MEDIA_DIR = Path(settings.MEDIA_ROOT)
except Exception:
    MEDIA_DIR = Path(__file__).resolve().parent.parent.parent / "media"

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
]

# Common English keyword translations for Bengali story concepts
CONCEPT_TRANSLATIONS = {
    "school": "cartoon elementary school classroom building exterior sunny morning",
    "road": "rural village dirt road sunny morning children storybook",
    "village": "peaceful countryside village huts green trees sunny",
    "forest": "lush green enchanted jungle forest sunlight filtering through trees",
    "river": "peaceful scenic riverbank gentle water ripples afternoon light",
    "house": "cozy storybook cottage house living room interior warm lighting",
    "garden": "flowering sunny garden green lawn colorful flowers",
    "market": "busy village bazaar marketplace colorful stalls",
    "park": "children playground green park sunny day",
    "night": "starry night sky cozy forest moonlit",
    "morning": "golden sunrise meadow morning dew peaceful",
    "evening": "warm orange sunset over hills evening glow",
    "rain": "gentle rainy day puddle reflections cozy atmosphere",
    "wallet": "lost brown leather wallet lying on road grass close up",
}


def download_image_from_url(url: str, save_path: Path, timeout: int = 25) -> bool:
    """Download image data and verify it is a valid picture."""
    try:
        headers = {"User-Agent": USER_AGENTS[0], "Accept": "image/*,*/*;q=0.8"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as res:
            content_type = res.headers.get("Content-Type", "")
            data = res.read()
            if len(data) > 8000 and ("image" in content_type or url.endswith((".jpg", ".png", ".jpeg", ".webp"))):
                save_path.parent.mkdir(parents=True, exist_ok=True)
                with open(save_path, "wb") as f:
                    f.write(data)
                logger.info(f"Successfully downloaded web asset to {save_path} ({len(data)} bytes)")
                return True
    except Exception as e:
        logger.debug(f"Failed to download from {url}: {e}")
    return False


def fetch_from_duckduckgo(query: str, save_path: Path) -> bool:
    """Search DuckDuckGo Images and download the best matching picture."""
    try:
        token_url = "https://duckduckgo.com/?q=" + urllib.parse.quote(query)
        req = urllib.request.Request(token_url, headers={"User-Agent": USER_AGENTS[0]})
        with urllib.request.urlopen(req, timeout=5) as res:
            html = res.read().decode("utf-8", errors="ignore")

        vqd_match = re.search(r'vqd=([0-9-]+)', html)
        if not vqd_match:
            return False
        vqd = vqd_match.group(1)

        api_url = f"https://duckduckgo.com/i.js?l=us-en&o=json&q={urllib.parse.quote(query)}&vqd={vqd}&f=,,,&p=1"
        req2 = urllib.request.Request(api_url, headers={
            "User-Agent": USER_AGENTS[0],
            "Referer": "https://duckduckgo.com/"
        })
        with urllib.request.urlopen(req2, timeout=6) as res2:
            data = json.loads(res2.read().decode())
            results = data.get("results", [])

        for r in results[:6]:
            img_url = r.get("image")
            if img_url and download_image_from_url(img_url, save_path):
                return True
    except Exception as e:
        logger.warning(f"DuckDuckGo search error for '{query}': {e}")
    return False


def fetch_from_wikimedia(query: str, save_path: Path) -> bool:
    """Fallback search on Wikimedia Commons for free public domain illustrations."""
    try:
        api_url = (
            "https://commons.wikimedia.org/w/api.php?action=query&format=json"
            f"&generator=search&gsrnamespace=6&gsrlimit=5&gsrsearch={urllib.parse.quote(query)}"
            "&prop=imageinfo&iiprop=url"
        )
        req = urllib.request.Request(api_url, headers={"User-Agent": "vmaker-auto-fetcher/1.0"})
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.loads(res.read().decode())
            pages = data.get("query", {}).get("pages", {})

        for pid, page in pages.items():
            info = page.get("imageinfo", [{}])[0]
            url = info.get("url")
            if url and download_image_from_url(url, save_path):
                return True
    except Exception as e:
        logger.warning(f"Wikimedia search error for '{query}': {e}")
    return False


def fetch_web_background(key: str, context_text: str = "") -> str:
    """
    Find and download a matching 3D/Pixar style background picture from the web.
    Saves to media/backgrounds/<key>.jpg and returns relative path.
    """
    clean_key = re.sub(r"[^\w-]", "", key.lower().strip())
    if not clean_key:
        clean_key = "default"

    bg_dir = MEDIA_DIR / "backgrounds"
    bg_dir.mkdir(parents=True, exist_ok=True)

    # Check if already exists locally
    for ext in [".jpg", ".jpeg", ".png", ".webp"]:
        candidate = bg_dir / f"{clean_key}{ext}"
        if candidate.exists() and candidate.stat().st_size > 5000:
            return f"backgrounds/{candidate.name}"

    save_path = bg_dir / f"{clean_key}.jpg"

    # Build refined query for Pixar/Disney children's story aesthetic
    concept = CONCEPT_TRANSLATIONS.get(clean_key, clean_key)
    query = f"pixar 3d animation background {concept} 16:9 storybook wallpaper"

    logger.info(f"Auto-fetching background for '{clean_key}' from web...")

    # Try DuckDuckGo first, then Wikimedia fallback
    if fetch_from_duckduckgo(query, save_path):
        return f"backgrounds/{clean_key}.jpg"

    if fetch_from_wikimedia(f"{clean_key} cartoon illustration wallpaper", save_path):
        return f"backgrounds/{clean_key}.jpg"

    # Default fallback
    return "backgrounds/default.jpg"


def fetch_web_character(key: str) -> str:
    """
    Find and download a matching 3D cartoon character sprite from the web.
    Saves to media/characters/<key>.png or .jpg and returns relative path.
    """
    clean_key = re.sub(r"[^\w-]", "", key.lower().strip())
    if not clean_key:
        clean_key = "character"

    char_dir = MEDIA_DIR / "characters"
    char_dir.mkdir(parents=True, exist_ok=True)

    # Check if already exists locally
    for ext in [".png", ".jpg", ".jpeg", ".webp"]:
        candidate = char_dir / f"{clean_key}{ext}"
        if candidate.exists() and candidate.stat().st_size > 5000:
            return f"characters/{candidate.name}"

    save_path = char_dir / f"{clean_key}.jpg"

    # Map Bengali/English names to cartoon archetypes
    name_archetypes = {
        "rahat": "cute 3d pixar cartoon school boy with backpack",
        "warina": "cute 3d pixar cartoon girl with red cap",
        "rahim": "cute 3d pixar cartoon boy friendly smiling",
        "rabbit": "cute 3d pixar fluffy cartoon bunny rabbit",
        "duck": "cute 3d pixar cartoon baby duckling",
        "owl": "cute 3d pixar cartoon wise owl bird",
        "bird": "cute 3d pixar colorful cartoon songbird",
        "cat": "cute 3d pixar fluffy cartoon kitten",
        "dog": "cute 3d pixar cartoon puppy dog",
    }
    archetype = name_archetypes.get(clean_key, f"cute 3d pixar cartoon character {clean_key}")
    query = f"{archetype} isolated character 3d model portrait"

    logger.info(f"Auto-fetching character for '{clean_key}' from web...")

    if fetch_from_duckduckgo(query, save_path):
        return f"characters/{clean_key}.jpg"

    return "scenes/pixar/panda_scene_1.jpg"


BENGALI_CONCEPT_MAP = {
    # Environments
    "জঙ্গল": "lush enchanted bamboo jungle forest with giant green trees and blooming wild flowers",
    "বন": "lush enchanted bamboo jungle forest with morning sunbeams filtering through giant trees",
    "গাছ": "majestic ancient forest trees with lush green foliage",
    "নদী": "sparkling crystal clear river winding through green hills with gentle water ripples",
    "পানি": "gentle flowing clear river water with sunny ripples",
    "স্কুল": "charming storybook school building with sunny playground and green lawn",
    "রাস্তা": "sunlit winding dirt pathway through peaceful countryside",
    "পথ": "scenic sunlit forest path with colorful wildflowers",
    "গ্রাম": "quaint storybook village with cozy thatched cottages and blooming gardens",
    "বাড়ি": "cozy whimsical storybook wooden cottage with glowing warm windows",
    "ঘর": "warm cozy cottage interior with wooden furniture and soft morning window light",
    "পাহাড়": "majestic rolling green hills and misty mountains in the distance",
    "ফুল": "colorful vibrant blooming flowers and glowing wildflowers",
    "প্রজাপতি": "magical glowing colorful butterflies fluttering gently in the air",
    "মাঠ": "wide open sunlit green meadow with wildflowers",
    "আকাশ": "clear blue sunny sky with fluffy white cotton clouds",
    "সূর্য": "radiant golden morning sun with brilliant volumetric light rays",
    "সকাল": "peaceful golden morning with warm sunrise glow and gentle mist",
    "সন্ধ্যা": "warm orange sunset twilight glowing over the landscape",
    "রাত": "magical starry night with soft glowing moon and twinkling fireflies",
    "বৃষ্টি": "gentle refreshing storybook rain with shiny wet leaves and puddle reflections",
    # Actions & Moods
    "হাঁট": "happily walking forward on an adventure",
    "দৌড়": "joyfully running through the landscape",
    "খেল": "playfully exploring with wide curious eyes",
    "দেখ": "looking around with wonder and excitement",
    "হাস": "big happy delighted joyful smile",
    "ভাব": "thoughtful curious expression wondering about the world",
    "খুঁজ": "curiously searching around the bushes",
    "হাত": "waving hand in friendly greeting",
    "ডাক": "calling out happily to friends",
    "ঘুম": "peacefully resting and cozy sleepy expression"
}


def translate_scene_to_english_prompt(bengali_text: str) -> str:
    """Extract semantic English visual keywords from Bengali story text."""
    found_elements = []
    text_lower = (bengali_text or "").lower()
    for key, desc in BENGALI_CONCEPT_MAP.items():
        if key in text_lower:
            found_elements.append(desc)
    if not found_elements:
        found_elements.append("lush enchanted bamboo jungle forest with morning sunbeams filtering through giant trees")
    return ", ".join(found_elements[:3])


def generate_pixar_scene_visual(
    scene_desc: str,
    char_name: str = "panda",
    shot_type: str = "medium",
    save_path: Path = None,
    seed: int = 42,
    scene_index: int = 0
) -> bool:
    """
    Generate an integrated 3D Pixar / Disney storybook animation scene.
    Uses AI Image Generation (Pollinations Sana model) with rich 3D cinematic prompt engineering.
    Falls back gracefully to high-res curated 3D Pixar frames if API rate limits (402) apply.
    """
    import shutil

    char_prompts = {
        "piku": "adorable cute baby panda with big expressive eyes and little red backpack, detailed fluffy fur",
        "panda": "adorable cute baby panda with big expressive eyes and little red backpack, detailed fluffy fur",
        "rahat": "cute little 3D cartoon boy with backpack, friendly warm smile, Pixar style",
        "warina": "cute 3D cartoon girl with red cap and sweet smile, Pixar style",
        "rabbit": "cute fluffy bunny rabbit with big ears, Pixar style",
        "bird": "cute colorful little baby bird, Pixar style",
        "cat": "cute fluffy playful kitten, Pixar style",
        "dog": "cute friendly puppy, Pixar style"
    }

    clean_char = (char_name or "panda").lower().strip()
    if any(w in (scene_desc or "") for w in ["পিকু", "পান্ডা", "জঙ্গল", "বন"]):
        clean_char = "panda"

    char_desc = char_prompts.get(clean_char, f"cute 3D cartoon character {clean_char}, Pixar style")
    english_env = translate_scene_to_english_prompt(scene_desc)

    prompt = (
        f"Pixar 3D Disney animation style, {char_desc}, {english_env}, "
        "lush magical storybook world, cinematic volumetric sunlight, "
        "god rays, rich vibrant lighting, Octane 3D render, highly detailed, "
        "children movie frame, 16:9 widescreen"
    )

    encoded = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1280&height=720&model=sana&nologo=true&seed={seed}"
    logger.info(f"Generating 3D Pixar scene visual for: {scene_desc[:40]}...")

    # Attempt dynamic AI generation
    success = download_image_from_url(url, save_path, timeout=20)
    if success and save_path and save_path.exists() and save_path.stat().st_size > 8000:
        return True

    # High-quality 3D Pixar Curated Fallback (Guarantees zero 2D cutouts or blanks)
    pixar_dir = MEDIA_DIR / "scenes" / "pixar"
    pixar_dir.mkdir(parents=True, exist_ok=True)
    fallback_pool = [
        pixar_dir / "panda_scene_1.jpg",
        pixar_dir / "panda_scene_2.jpg",
        pixar_dir / "panda_scene_3.jpg",
        pixar_dir / "panda_scene_4.jpg",
        pixar_dir / "panda_scene_5.jpg",
    ]

    # Pick best frame by scene keywords or index
    chosen_frame = None
    desc_low = (scene_desc or "").lower()
    if any(w in desc_low for w in ["ঘর", "বাড়ি", "ঘুম", "সকাল", "উঠে"]):
        chosen_frame = pixar_dir / "panda_scene_1.jpg"
    elif any(w in desc_low for w in ["হাঁট", "পথ", "ফুল", "প্রজাপতি"]):
        chosen_frame = pixar_dir / "panda_scene_2.jpg"
    elif any(w in desc_low for w in ["বাঁশ", "খেতে", "খাবার", "বসে"]):
        chosen_frame = pixar_dir / "panda_scene_3.jpg"
    elif any(w in desc_low for w in ["নদী", "পানি", "স্রোত", "হাত"]):
        chosen_frame = pixar_dir / "panda_scene_4.jpg"
    else:
        chosen_frame = fallback_pool[scene_index % len(fallback_pool)]

    if chosen_frame and chosen_frame.exists():
        if save_path:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(chosen_frame, save_path)
            logger.info(f"Deployed curated 3D Pixar frame {chosen_frame.name} to {save_path.name}")
            return True

    return False
