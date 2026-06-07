import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
DB_PATH = BASE_DIR / "favorites.db"

DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DB_PATH}")

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
MODEL_NAME = os.environ.get("MODEL_NAME", "gemini-1.5-pro")

DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]

MAX_HISTORY_MESSAGES = int(os.environ.get("MAX_HISTORY_MESSAGES", "20"))
RECIPE_CACHE_TTL_HOURS = int(os.environ.get("RECIPE_CACHE_TTL_HOURS", "168"))
RATE_LIMIT_CHAT = os.environ.get("RATE_LIMIT_CHAT", "30/minute")
RATE_LIMIT_SEARCH = os.environ.get("RATE_LIMIT_SEARCH", "20/minute")

SEARCH_SITES = [
    "yemek.com",
    "nefisyemektarifleri.com",
    "lezzet.com.tr",
]

CATEGORY_ORDER = [
    "corbalar",
    "tavuk",
    "kirmizi_et",
    "balik",
    "bakliyat",
    "sebze",
    "fit_tarifler",
    "fit_tatlilar",
    "zararli_lezzetli",
]

CATEGORY_META = {
    "corbalar": {"label": "Çorbalar", "emoji": "🍲", "color": "#fef3c7"},
    "tavuk": {"label": "Tavuk", "emoji": "🍗", "color": "#fff7ed"},
    "kirmizi_et": {"label": "Kırmızı Et", "emoji": "🥩", "color": "#fef2f2"},
    "balik": {"label": "Balık", "emoji": "🐟", "color": "#fdf4ff"},
    "bakliyat": {"label": "Bakliyat", "emoji": "🫘", "color": "#fefce8"},
    "sebze": {"label": "Sebze", "emoji": "🥦", "color": "#f0fdf4"},
    "fit_tarifler": {"label": "Fit Tarifler", "emoji": "🥗", "color": "#f0f9ff"},
    "fit_tatlilar": {"label": "Fit Tatlılar", "emoji": "🍓", "color": "#fdf2f8"},
    "zararli_lezzetli": {"label": "Zararlı ama Lezzetli", "emoji": "😋", "color": "#fffbeb"},
}

DEFAULT_PREFERENCES = {
    "person_count": "3",
    "meal_type": "Akşam yemeği",
    "style": "Ev yemeği (pratik, hafif, fit)",
    "preferences": "Düşük kalorili, proteinli, glutensiz, sebze ağırlıklı, tavuk veya dana eti, fırın veya tencere yemekleri",
    "dislikes": "Kuzu eti, Uzakdoğu mutfağı, Noodle, Soya sosu, Teriyaki, Sushi, Ramen, Wok tarzı yemekler",
}
