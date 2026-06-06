import json


class PreferencesTool:
    def __init__(self, db):
        self.db = db

    def show_preferences(self, user_id: str) -> str:
        prefs = self.db.get_preferences(user_id)

        criteria = json.loads(prefs["criteria"])
        exclusions = json.loads(prefs["exclusions"])

        lines = [
            "Yemek tercihlerin:",
            "",
            f"Kişi sayısı: {prefs['people_count']}",
            f"Öğün: {prefs['meal_type']}",
            "",
            "Kriterler:",
        ]

        for item in criteria:
            lines.append(f"- {item}")

        lines.append("")
        lines.append("Hariç tutulacaklar:")

        for item in exclusions:
            lines.append(f"- {item}")

        lines.append("")
        lines.append("Öneri sayısı: 5")
        lines.append("Öneri kategorileri: Tavuk, Dana/Et, Sebze, Bakliyat, Fit Glutensiz")

        return "\n".join(lines)