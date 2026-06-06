import json
from tavily import TavilyClient
from app.config import settings
from app.llm import GroqLLM
from app.prompts import (
    BASE_MEAL_CRITERIA,
    FIVE_CATEGORY_INSTRUCTION,
    JSON_RECIPE_SELECTION_PROMPT,
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


class RecipeSearchTool:
    def __init__(self):
        self.tavily = TavilyClient(api_key=settings.tavily_api_key)
        self.llm = GroqLLM()

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
            search_query = cat["query"]

            if day_name:
                search_query += f" {day_name}"

            response = self.tavily.search(
                query=search_query,
                search_depth="basic",
                max_results=5,
                include_answer=False,
                include_raw_content=False,
            )

            for result in response.get("results", []):
                raw_results.append({
                    "intended_category": cat["name"],
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content": result.get("content", ""),
                    "score": result.get("score", 0),
                })

        user_prompt = f"""
Kullanıcı ID: {user_id}
Bağlam: {context}
Gün: {day_name or "bugün"}

Son dönemde yenmiş yemekler, mümkünse tekrar etme:
{json.dumps(recent_meals, ensure_ascii=False)}

Web arama sonuçları:
{json.dumps(raw_results, ensure_ascii=False, indent=2)}
"""

        selected = self.llm.json_chat(
            system=BASE_MEAL_CRITERIA + "\n" + FIVE_CATEGORY_INSTRUCTION + "\n" + JSON_RECIPE_SELECTION_PROMPT,
            user=user_prompt,
            temperature=0.1,
        )

        normalized = []
        for idx, item in enumerate(selected[:5], start=1):
            normalized.append({
                "option_no": idx,
                "category": item.get("category", ""),
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "source": item.get("source", ""),
            })

        return normalized

    @staticmethod
    def format_suggestions(title: str, candidates: list) -> str:
        lines = [title, ""]

        for item in candidates:
            lines.append(f"{item['option_no']}) [{item.get('category', '')}] {item['title']}")
            lines.append(item.get("url", ""))

        lines.append("")
        lines.append("Seçmek için 1, 2, 3, 4 veya 5 yazabilirsin.")
        return "\n".join(lines)
