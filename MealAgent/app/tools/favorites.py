class FavoritesTool:
    def __init__(self, db):
        self.db = db

    def add_last_selected_to_favorites(self, user_id: str) -> str:
        last = self.db.get_last_selected(user_id)

        if not last:
            return "Henüz favorilere ekleyebileceğim seçilmiş bir yemek yok."

        self.db.add_favorite(
            user_id=user_id,
            title=last["title"],
            url=last.get("url", ""),
            category=last.get("category", ""),
        )

        return f"Favorilere ekledim:\n{last['title']}\n{last.get('url', '')}"

    def list_favorites(self, user_id: str) -> str:
        favorites = self.db.list_favorites(user_id)

        if not favorites:
            return "Henüz favori yemeğin yok."

        lines = ["Favori yemeklerin:", ""]
        for idx, item in enumerate(favorites, start=1):
            lines.append(f"{idx}) [{item.get('category', '')}] {item['title']}")
            if item.get("url"):
                lines.append(item["url"])

        return "\n".join(lines)