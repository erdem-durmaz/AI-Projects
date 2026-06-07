import json
import re
from urllib.parse import urlparse

from tavily import TavilyClient

from app.config import settings
from app.llm import GroqLLM
from app.prompts import (
    BASE_MEAL_CRITERIA,
    FIVE_CATEGORY_INSTRUCTION,
    JSON_RECIPE_SELECTION_PROMPT,
    WEEKLY_15_RECIPE_SELECTION_PROMPT,
    WEEKLY_QUERY_GENERATION_PROMPT,
)


CATEGORIES = [
    {
        "name": "Tavuk",
        "query": "hafif fit glutensiz tavuk akşam yemeği tarifi ev yemeği",
    },
    {
        "name": "Dana/Et",
        "query": "kuzu olmayan dana etli hafif glutensiz akşam yemeği tarifi ev yemeği",
    },
    {
        "name": "Sebze",
        "query": "hafif fit glutensiz sebze yemeği tarifi akşam yemeği",
    },
    {
        "name": "Bakliyat",
        "query": "proteinli glutensiz bakliyat yemeği tarifi hafif akşam yemeği",
    },
    {
        "name": "Fit Glutensiz",
        "query": "fit glutensiz düşük kalorili pratik akşam yemeği tarifi",
    },
]


EXCLUDED_DOMAINS = [
    "instagram.com",
    "www.instagram.com",
    "tiktok.com",
    "www.tiktok.com",
    "youtube.com",
    "www.youtube.com",
    "youtu.be",
    "reddit.com",
    "www.reddit.com",
    "pinterest.com",
    "tr.pinterest.com",
    "facebook.com",
    "www.facebook.com",
    "x.com",
    "twitter.com",
    "onedio.com",
    "www.onedio.com",
    "acibadem.com.tr",
    "www.acibadem.com.tr",
    "migrostv.migros.com.tr",
    "migros.com.tr",
]


PREFERRED_DOMAINS = [
    "nefisyemektarifleri.com",
    "www.nefisyemektarifleri.com",
    "yemek.com",
    "www.yemek.com",
    "refikaninmutfagi.com",
    "www.refikaninmutfagi.com",
    "sofra.com.tr",
    "www.sofra.com.tr",
]


GENERIC_TITLE_KEYWORDS = [
    "fikir",
    "fikirleri",
    "liste",
    "listesi",
    "tarifler",
    "tarifleri",
    "25 tarif",
    "45 tarif",
    "10 yemek tarifi",
    "6 tarif",
    "besleyici ve fit",
    "diyet sebze yemekleri",
    "etsiz sebze yemekleri",
    "glutensiz tarifler",
    "düşük kalorili yemekler",
    "diyet yemekleri",
    "akşam yemeği fikirleri",
    "kolay akşam yemeği",
    "en iyi",
    "popüler",
    "kategori",
    "rehber",
    "nedir",
    "nelerdir",
    "sağlıklı beslenme",
    "saglikli beslenme",
    "et yemekleri",
    "sebze yemekleri",
    "tavuk yemekleri",
    "bakliyat yemekleri",
    "pinterest",
    "reddit",
]


BAD_RECIPE_KEYWORDS = [
    "kuzu",
    "noodle",
    "soya sosu",
    "teriyaki",
    "sushi",
    "ramen",
    "wok",
    "uzakdoğu",
    "asya",
    "thai",
    "çin",
    "japon",
    "kore",
    "quesadilla",
    "taco",
    "nachos",
    "burrito",
    "tagliata",
]


def get_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().replace("m.", "")
    except Exception:
        return ""


def is_excluded_domain(url: str) -> bool:
    domain = get_domain(url)
    return any(excluded in domain for excluded in EXCLUDED_DOMAINS)


def is_preferred_domain(url: str) -> bool:
    domain = get_domain(url)
    return any(preferred in domain for preferred in PREFERRED_DOMAINS)


def is_generic_title(title: str) -> bool:
    t = title.lower().strip()

    if not t:
        return True

    return any(keyword in t for keyword in GENERIC_TITLE_KEYWORDS)


def has_bad_keywords(text: str) -> bool:
    t = text.lower()
    return any(keyword in t for keyword in BAD_RECIPE_KEYWORDS)


def is_bad_url_pattern(url: str) -> bool:
    url_lower = url.lower()

    bad_patterns = [
        "/liste/",
        "/kategori/",
        "/saglikli-beslenme",
        "/sağlıklı-beslenme",
        "/et-yemekleri",
        "/sebze-yemekleri",
        "/tavuk-yemekleri",
        "/bakliyat",
        "/glutensiz-beslenme",
        "/hayat/",
        "/haber/",
        "/maraton-haftasinda",
        "/protein-kaynagi",
        "/diyet-sebze-yemekleri",
        "/etsiz-sebze-yemekleri",
    ]

    return any(pattern in url_lower for pattern in bad_patterns)


def is_specific_recipe_url(url: str) -> bool:
    url_lower = url.lower()
    domain = get_domain(url)

    if is_excluded_domain(url):
        return False

    if is_bad_url_pattern(url):
        return False

    if "nefisyemektarifleri.com" in domain:
        return (
            "/liste/" not in url_lower
            and "/kategori/" not in url_lower
            and (
                "tarifi" in url_lower
                or "yemegi" in url_lower
                or "yemeği" in url_lower
            )
        )

    if "yemek.com" in domain:
        return "/tarif/" in url_lower

    if "refikaninmutfagi.com" in domain:
        return not any(x in url_lower for x in [
            "saglikli-beslenme",
            "sağlıklı-beslenme",
            "et-yemekleri",
            "sebze-yemekleri",
            "tavuk-yemekleri",
            "kategori",
        ])

    if "sofra.com.tr" in domain:
        return "/tarif/" in url_lower

    return False


def looks_like_specific_recipe(title: str, url: str, content: str = "") -> bool:
    if not title or not url:
        return False

    if is_excluded_domain(url):
        return False

    if is_bad_url_pattern(url):
        return False

    if not is_specific_recipe_url(url):
        return False

    combined = f"{title} {url} {content}".lower()

    if has_bad_keywords(combined):
        return False

    if is_generic_title(title):
        return False

    recipe_signals = [
        "tarifi",
        "yemeği",
        "yemegi",
        "köfte",
        "tavuk",
        "kabak",
        "patlıcan",
        "karnabahar",
        "brokoli",
        "nohut",
        "mercimek",
        "fasulye",
        "türlü",
        "dolma",
        "sote",
        "fırında",
        "tencere",
        "sebzeli",
        "etli",
        "zeytinyağlı",
        "graten",
        "bezelye",
        "ıspanak",
    ]

    return any(signal in combined for signal in recipe_signals)


class RecipeSearchTool:
    def __init__(self):
        self.tavily = TavilyClient(api_key=settings.tavily_api_key)
        self.llm = GroqLLM()

    # ------------------------------------------------------------------
    # Daily 5 Suggestions
    # ------------------------------------------------------------------

    def get_five_category_suggestions(
        self,
        user_id: str,
        db,
        day_name: str | None = None,
        context: str = "daily",
    ) -> list:
        recent_meals = db.get_recent_meals(user_id, limit=10)
        raw_results = []

        for cat in CATEGORIES:
            search_query = self._build_preferred_domain_query(cat["query"])

            if day_name:
                search_query += f" {day_name}"

            results = self._safe_tavily_search(
                query=search_query,
                max_results=10,
                use_domain_params=True,
            )

            for result in results:
                self._append_valid_result(raw_results, result, cat["name"])

        if len(raw_results) < 10:
            for cat in CATEGORIES:
                search_query = cat["query"]

                if day_name:
                    search_query += f" {day_name}"

                results = self._safe_tavily_search(
                    query=search_query,
                    max_results=10,
                    use_domain_params=False,
                )

                for result in results:
                    self._append_valid_result(raw_results, result, cat["name"])

        raw_results = self._deduplicate_results(raw_results)

        if not raw_results:
            return []

        user_prompt = f"""
Kullanıcı ID: {user_id}
Bağlam: {context}
Gün: {day_name or "bugün"}

Son dönemde yenmiş yemekler, mümkünse tekrar etme:
{json.dumps(recent_meals, ensure_ascii=False)}

Web arama sonuçları:
{json.dumps(raw_results, ensure_ascii=False, indent=2)}

Kurallar:
- Sadece spesifik yemek tarifi sayfası seç.
- Genel kategori/liste/sosyal medya/haber/sağlık rehberi sayfası seçme.
- Kuzu eti ve Uzakdoğu mutfağı seçme.
"""

        try:
            selected = self.llm.json_chat(
                system=BASE_MEAL_CRITERIA + "\n" + FIVE_CATEGORY_INSTRUCTION + "\n" + JSON_RECIPE_SELECTION_PROMPT,
                user=user_prompt,
                temperature=0.05,
            )
        except Exception:
            selected = []

        normalized = self._normalize_llm_selection_from_raw(
            selected=selected,
            raw_results=raw_results,
            max_items=5,
        )

        if len(normalized) < 5:
            normalized = self._fill_missing_from_raw_results(
                normalized=normalized,
                raw_results=raw_results,
                max_items=5,
            )

        return normalized[:5]

    # ------------------------------------------------------------------
    # Weekly Dynamic Query Generation
    # ------------------------------------------------------------------

    def generate_weekly_search_queries(self, user_id: str, db) -> list:
        recent_meals = db.get_recent_meals(user_id, limit=15)

        user_prompt = f"""
Kullanıcı ID: {user_id}

Son dönemde yenmiş yemekler:
{json.dumps(recent_meals, ensure_ascii=False)}

Bu yemekleri mümkünse tekrar ettirmeyecek şekilde 25 adet arama sorgusu üret.
Sorgular Türkçe olsun.
"""

        try:
            queries = self.llm.json_chat(
                system=BASE_MEAL_CRITERIA + "\n" + WEEKLY_QUERY_GENERATION_PROMPT,
                user=user_prompt,
                temperature=0.4,
            )
        except Exception:
            queries = []

        valid_queries = []

        allowed_categories = {
            "Tavuk",
            "Dana/Et",
            "Sebze",
            "Bakliyat",
            "Fit Glutensiz",
        }

        for item in queries:
            category = item.get("category", "").strip()
            query = item.get("query", "").strip()

            if category not in allowed_categories:
                continue

            if not query:
                continue

            if self._query_has_bad_terms(query):
                continue

            valid_queries.append({
                "category": category,
                "query": query,
            })

        return valid_queries[:25]

    def _query_has_bad_terms(self, query: str) -> bool:
        q = query.lower()

        bad_terms = [
            "kuzu",
            "noodle",
            "soya sosu",
            "teriyaki",
            "sushi",
            "ramen",
            "wok",
            "uzakdoğu",
            "asya",
            "thai",
            "çin",
            "japon",
            "kore",
            "quesadilla",
            "taco",
            "nachos",
            "burrito",
            "liste",
            "listesi",
            "fikirleri",
            "kategori",
        ]

        return any(term in q for term in bad_terms)

    # ------------------------------------------------------------------
    # Weekly Suggestions
    # ------------------------------------------------------------------

    def get_weekly_15_suggestions(
        self,
        user_id: str,
        db,
        context: str = "weekly_bulk",
    ) -> list:
        """
        Haftalık plan için dinamik tarif araması yapar.
        Hedef 15 öneri.
        Minimum 7 kaliteli öneri bulursa liste gösterilir.
        """

        recent_meals = db.get_recent_meals(user_id, limit=15)

        search_queries = self.generate_weekly_search_queries(
            user_id=user_id,
            db=db,
        )

        if not search_queries:
            return []

        raw_results = []

        for item in search_queries:
            category = item["category"]
            query = item["query"]

            search_query = (
                f"{query} "
                f"(site:nefisyemektarifleri.com OR site:yemek.com OR "
                f"site:refikaninmutfagi.com OR site:sofra.com.tr)"
            )

            results = self._safe_tavily_search(
                query=search_query,
                max_results=12,
                use_domain_params=True,
            )

            for result in results:
                self._append_valid_result(
                    raw_results=raw_results,
                    result=result,
                    intended_category=category,
                )

        raw_results = self._deduplicate_results(raw_results)

        recent_normalized = {
            self._normalize_title(title)
            for title in recent_meals
        }

        filtered_results = []

        for item in raw_results:
            title_norm = self._normalize_title(item.get("title", ""))

            if title_norm in recent_normalized:
                continue

            filtered_results.append(item)

        if len(filtered_results) >= 7:
            raw_results = filtered_results

        if len(raw_results) < 7:
            return []

        user_prompt = f"""
Kullanıcı ID: {user_id}
Bağlam: {context}

Son dönemde yenmiş yemekler:
{json.dumps(recent_meals, ensure_ascii=False)}

Groq tarafından üretilen arama sorguları:
{json.dumps(search_queries, ensure_ascii=False, indent=2)}

Filtrelenmiş ve doğrulanmış tarif adayları:
{json.dumps(raw_results, ensure_ascii=False, indent=2)}

Görev:
- Bu adaylar arasından haftalık plan için en uygun tarifleri seç.
- Mümkünse 15 tarif seç.
- En az 7 tarif seç.
- Sadece verilen aday URL'lerinden seçim yap.
- URL uydurma.
- Başlık uydurma.
- Genel liste/kategori/haber/sosyal medya/sağlık rehberi linki seçme.
- Kuzu eti ve Uzakdoğu mutfağı seçme.
- Kategori dengesini mümkün olduğunca koru.
- Sadece geçerli JSON dön.
"""

        try:
            selected = self.llm.json_chat(
                system=BASE_MEAL_CRITERIA + "\n" + WEEKLY_15_RECIPE_SELECTION_PROMPT,
                user=user_prompt,
                temperature=0.05,
            )
        except Exception:
            selected = []

        normalized = self._normalize_llm_selection_from_raw(
            selected=selected,
            raw_results=raw_results,
            max_items=15,
        )

        if len(normalized) < 15:
            normalized = self._fill_missing_from_raw_results(
                normalized=normalized,
                raw_results=raw_results,
                max_items=15,
            )

        if len(normalized) < 7:
            return []

        return normalized[:15]

    # ------------------------------------------------------------------
    # Search Helpers
    # ------------------------------------------------------------------

    def _build_preferred_domain_query(self, base_query: str) -> str:
        return (
            f"({base_query}) "
            f"(site:nefisyemektarifleri.com OR site:yemek.com OR "
            f"site:refikaninmutfagi.com OR site:sofra.com.tr)"
        )

    def _safe_tavily_search(
        self,
        query: str,
        max_results: int = 10,
        use_domain_params: bool = True,
    ) -> list:
        try:
            if use_domain_params:
                response = self.tavily.search(
                    query=query,
                    search_depth="advanced",
                    max_results=max_results,
                    include_answer=False,
                    include_raw_content=False,
                    include_domains=PREFERRED_DOMAINS,
                    exclude_domains=EXCLUDED_DOMAINS,
                )
            else:
                response = self.tavily.search(
                    query=query,
                    search_depth="advanced",
                    max_results=max_results,
                    include_answer=False,
                    include_raw_content=False,
                    exclude_domains=EXCLUDED_DOMAINS,
                )

            return response.get("results", [])

        except TypeError:
            response = self.tavily.search(
                query=query,
                search_depth="advanced",
                max_results=max_results,
                include_answer=False,
                include_raw_content=False,
            )
            return response.get("results", [])

        except Exception:
            return []

    def _append_valid_result(self, raw_results: list, result: dict, intended_category: str):
        title = result.get("title", "")
        url = result.get("url", "")
        content = result.get("content", "")

        if not looks_like_specific_recipe(title, url, content):
            return

        raw_results.append({
            "intended_category": intended_category,
            "title": title,
            "url": url,
            "content": content,
            "source": get_domain(url),
            "score": result.get("score", 0),
            "preferred_domain": is_preferred_domain(url),
        })

    def _deduplicate_results(self, results: list) -> list:
        seen_urls = set()
        seen_titles = set()
        unique = []

        results = sorted(
            results,
            key=lambda x: (
                not x.get("preferred_domain", False),
                -float(x.get("score", 0) or 0),
            )
        )

        for item in results:
            url = item.get("url", "")
            title = self._normalize_title(item.get("title", ""))

            if not url or not title:
                continue

            if url in seen_urls:
                continue

            if title in seen_titles:
                continue

            if is_bad_url_pattern(url):
                continue

            if is_excluded_domain(url):
                continue

            seen_urls.add(url)
            seen_titles.add(title)
            unique.append(item)

        return unique

    def _normalize_title(self, title: str) -> str:
        title = title.lower().strip()
        title = re.sub(r"\s+", " ", title)
        title = title.replace("tarifi", "").strip()
        title = title.replace("- nefis yemek tarifleri", "").strip()
        title = title.replace("- yemek.com", "").strip()
        return title

    def _normalize_llm_selection_from_raw(
        self,
        selected: list,
        raw_results: list,
        max_items: int,
    ) -> list:
        raw_by_url = {
            item["url"]: item
            for item in raw_results
            if item.get("url")
        }

        normalized = []

        for item in selected:
            url = item.get("url", "")

            if url not in raw_by_url:
                continue

            raw_item = raw_by_url[url]
            title = raw_item.get("title", "")
            category = raw_item.get("intended_category", item.get("category", ""))
            source = raw_item.get("source", get_domain(url))
            content = raw_item.get("content", "")

            if not looks_like_specific_recipe(title, url, content):
                continue

            normalized.append({
                "option_no": len(normalized) + 1,
                "category": category,
                "title": title,
                "url": url,
                "source": source,
            })

            if len(normalized) >= max_items:
                break

        return normalized

    def _fill_missing_from_raw_results(
        self,
        normalized: list,
        raw_results: list,
        max_items: int,
    ) -> list:
        existing_titles = {self._normalize_title(x.get("title", "")) for x in normalized}
        existing_urls = {x.get("url", "") for x in normalized}

        for item in raw_results:
            if len(normalized) >= max_items:
                break

            title = item.get("title", "")
            url = item.get("url", "")
            content = item.get("content", "")

            normalized_title = self._normalize_title(title)

            if normalized_title in existing_titles:
                continue

            if url in existing_urls:
                continue

            if not looks_like_specific_recipe(title, url, content):
                continue

            normalized.append({
                "option_no": len(normalized) + 1,
                "category": item.get("intended_category", ""),
                "title": title,
                "url": url,
                "source": item.get("source", get_domain(url)),
            })

            existing_titles.add(normalized_title)
            existing_urls.add(url)

        return normalized

    # ------------------------------------------------------------------
    # Formatters
    # ------------------------------------------------------------------

    @staticmethod
    def format_suggestions(title: str, candidates: list) -> str:
        if not candidates:
            return (
                "Uygun spesifik tarif bulamadım. "
                "Arama filtreleri fazla dar kalmış olabilir. "
                "Tekrar denemek için /bugun yazabilirsin."
            )

        lines = [title, ""]

        for item in candidates:
            lines.append(f"{item['option_no']}) [{item.get('category', '')}] {item['title']}")
            lines.append(item.get("url", ""))

        lines.append("")
        lines.append("Seçmek için 1, 2, 3, 4 veya 5 yazabilirsin.")

        return "\n".join(lines)

    @staticmethod
    def format_weekly_15_suggestions(candidates: list) -> str:
        if not candidates:
            return (
                "Haftalık plan için yeterli sayıda uygun ve spesifik tarif bulamadım.\n\n"
                "Genel liste, kategori, haber, sosyal medya ve sağlık rehberi sayfalarını eledim.\n"
                "Tekrar denemek için /haftalik_plan yazabilirsin."
            )

        count = len(candidates)

        if count == 15:
            lines = ["Haftalık plan için 15 yemek seçeneği:", ""]
        else:
            lines = [f"Haftalık plan için {count} kaliteli yemek seçeneği buldum:", ""]

        for item in candidates:
            lines.append(f"{item['option_no']}) [{item.get('category', '')}] {item['title']}")
            lines.append(item.get("url", ""))

        lines.append("")

        if count < 15:
            lines.append(
                "Not: 15 seçeneğe tamamlamak yerine sadece kaliteli ve spesifik tarifleri gösteriyorum."
            )
            lines.append("")

        lines.append("Haftalık planını yapmak için 7 seçim yaz.")
        lines.append("Örnek:")
        lines.append("1, 2, 3, 4, 5, 6, 7")
        lines.append("")
        lines.append("Bu sıralama Pazartesi'den Pazar'a kaydedilir.")

        return "\n".join(lines)