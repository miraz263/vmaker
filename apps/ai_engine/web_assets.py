"""
Auto Web Asset Fetcher for vmaker
Automatically discovers, searches, and downloads Pixar/3D-style
backgrounds and character visuals from the web when not available locally.
"""

import os
import random
import re
import urllib.error
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

    return f"characters/{clean_key}.jpg"


def _is_valid_image(path: Path) -> bool:
    try:
        from PIL import Image
        with Image.open(path) as im:
            im.verify()
        return path.stat().st_size > 8000
    except Exception:
        return False


def _placeholder_frame(save_path: Path, seed: int) -> None:
    """Soft gradient frame used only when every image service fails."""
    from PIL import Image, ImageDraw
    rnd = random.Random(seed)
    top = (rnd.randint(120, 200), rnd.randint(170, 230), rnd.randint(200, 255))
    bottom = (rnd.randint(60, 120), rnd.randint(120, 180), rnd.randint(60, 120))
    w, h = 1280, 720
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        draw.line([(0, y), (w, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))
    save_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(save_path, "JPEG", quality=90)


_last_pollinations_call = 0.0


def _fetch_pollinations(url: str, save_path: Path, token: str | None) -> str:
    """Returns "ok", "rate_limited" or "error"."""
    headers = {"User-Agent": USER_AGENTS[0], "Accept": "image/*"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=120) as res:
            data = res.read()
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(data)
        return "ok" if _is_valid_image(save_path) else "error"
    except urllib.error.HTTPError as e:
        if e.code in (402, 429):
            return "rate_limited"
        logger.warning(f"Pollinations HTTP {e.code}")
    except Exception as e:
        logger.warning(f"Pollinations request failed: {e}")
    return "error"


def generate_scene_image(prompt: str, save_path: Path, seed: int = 42) -> str:
    """
    Generate one scene picture with the free Pollinations API.

    Without a key Pollinations allows 1 image every 45 seconds per IP, so calls are
    spaced out (POLLINATIONS_INTERVAL, default 47s). With POLLINATIONS_TOKEN set the
    wait is skipped. Tries the models in POLLINATIONS_MODELS in order.
    Returns the model that worked, or "placeholder".
    """
    import time
    global _last_pollinations_call

    token = os.getenv("POLLINATIONS_TOKEN") or None
    interval = 0.0 if token else float(os.getenv("POLLINATIONS_INTERVAL", "47"))
    models = [m.strip() for m in os.getenv("POLLINATIONS_MODELS", "flux,turbo").split(",") if m.strip()]
    encoded = urllib.parse.quote(prompt[:1800])

    for model in models:
        for attempt in range(3):
            wait = _last_pollinations_call + interval - time.time()
            if wait > 0:
                logger.info(f"Waiting {wait:.0f}s for Pollinations free limit")
                time.sleep(wait)
            _last_pollinations_call = time.time()

            url = (
                f"https://image.pollinations.ai/prompt/{encoded}"
                f"?width=1280&height=720&model={model}&seed={seed}&nologo=true&enhance=false"
            )
            logger.info(f"Pollinations ({model}, try {attempt + 1}) for {save_path.name}")
            result = _fetch_pollinations(url, save_path, token)
            if result == "ok":
                return model
            if result == "error":
                break  # try the next model

    logger.warning(f"All image services failed for {save_path.name}; using placeholder frame")
    _placeholder_frame(save_path, seed)
    return "placeholder"
