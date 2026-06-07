import json
import logging
import re

import httpx

from app.config import SEARCH_SITES, TAVILY_API_KEY
from app.db import db_get_cached_recipe, db_set_cached_recipe
from app.llm import parse_page_content, random_meal_name

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9",
}


def slugify(name: str) -> str:
    tr_map = str.maketrans("çğışöüÇĞİŞÖÜ", "cgisoucgisoU")
    s = name.lower().translate(tr_map)
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s.strip())
    return s


def tavily_search(query: str, max_results: int = 10) -> list:
    if not query.strip():
        query = random_meal_name()
        logger.info("Random search query: %s", query)

    if not TAVILY_API_KEY:
        logger.warning("TAVILY_API_KEY not set")
        return []

    try:
        payload = {
            "api_key": TAVILY_API_KEY,
            "query": f"{query} tarifi",
            "max_results": max_results,
            "search_depth": "basic",
            "include_answer": False,
            "include_domains": SEARCH_SITES,
        }
        r = httpx.post("https://api.tavily.com/search", json=payload, timeout=12)
        r.raise_for_status()
        data = r.json()

        results = []
        seen = set()
        for item in data.get("results", []):
            title = item.get("title", "").strip()
            url = item.get("url", "")
            clean = re.split(r"[|\-–]", title)[0].strip()
            clean = re.sub(
                r"(?i)(tarif[i]?|nasıl yapılır|yapılışı|malzemeleri).*$",
                "",
                clean,
            ).strip()
            clean = clean.strip(" ,.:")
            if len(clean) < 3 or clean.lower() in seen:
                continue
            seen.add(clean.lower())
            results.append({"name": clean, "url": url, "title": title})

        logger.info("Tavily returned %d results for '%s'", len(results), query)
        return results
    except Exception as e:
        logger.exception("Tavily search failed: %s", e)
        return []


def fetch_page(url: str) -> dict:
    cached = db_get_cached_recipe(url)
    if cached:
        logger.info("Recipe cache hit: %s", url[:60])
        return cached

    try:
        r = httpx.get(url, headers=HEADERS, timeout=12, follow_redirects=True)
        r.raise_for_status()
        raw_html = r.text

        clean_text = re.sub(r"<script[^>]*>.*?</script>", " ", raw_html, flags=re.DOTALL)
        clean_text = re.sub(r"<style[^>]*>.*?</style>", " ", clean_text, flags=re.DOTALL)
        clean_text = re.sub(r"<[^>]+>", " ", clean_text)
        clean_text = re.sub(r"\s+", " ", clean_text).strip()

        if len(clean_text) < 200:
            return {"type": "error", "error": "Sayfa içeriği okunamadı"}

        data = parse_page_content(clean_text)
        if data.get("type") in ("recipe", "list"):
            db_set_cached_recipe(url, data)
        logger.info("Fetched page type=%s url=%s", data.get("type"), url[:60])
        return data
    except json.JSONDecodeError:
        return {"type": "error", "error": "İçerik ayrıştırılamadı"}
    except Exception as e:
        logger.exception("fetch_page failed: %s", e)
        return {"type": "error", "error": "Sayfa yüklenemedi"}


def find_recipe_url(name: str) -> str | None:
    slug = slugify(name)
    candidates = [
        f"https://yemek.com/tarif/{slug}-tarifi/",
        f"https://yemek.com/tarif/{slug}/",
        f"https://www.nefisyemektarifleri.com/{slug}-tarifi",
        f"https://www.nefisyemektarifleri.com/{slug}",
        f"https://www.lezzet.com.tr/yemek-tarifleri/{slug}",
    ]
    for url in candidates:
        try:
            r = httpx.get(url, headers=HEADERS, timeout=8, follow_redirects=True)
            if r.status_code == 200 and len(r.text) > 2000:
                logger.info("Recipe URL found via slug: %s", r.url)
                return str(r.url)
        except Exception:
            continue

    if not TAVILY_API_KEY:
        return None

    try:
        r = httpx.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": f'"{name}" tarifi malzemeler yapılış',
                "max_results": 5,
                "include_domains": SEARCH_SITES,
            },
            timeout=10,
        )
        r.raise_for_status()
        for item in r.json().get("results", []):
            url = item.get("url", "")
            if any(p in url for p in ["/tarif/", "-tarifi", "/yemek/"]):
                if not any(
                    p in url
                    for p in ["liste", "kategori", "haberler", "/fit-", "/diyet", "pratik-"]
                ):
                    logger.info("Recipe URL found via Tavily: %s", url)
                    return url
    except Exception as e:
        logger.exception("Tavily recipe lookup failed: %s", e)
    return None
