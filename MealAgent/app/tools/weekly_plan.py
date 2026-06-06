import re


DAYS = [
    "Pazartesi",
    "Salı",
    "Çarşamba",
    "Perşembe",
    "Cuma",
    "Cumartesi",
    "Pazar",
]


class WeeklyPlanTool:
    def __init__(self, db, recipe_search_tool):
        self.db = db
        self.recipe_search_tool = recipe_search_tool

    def start_weekly_plan(self, user_id: str) -> str:
        """
        Haftalık plan akışı:
        - Tek seferde tarif önerileri üretir.
        - Hedef 15 seçenek.
        - Minimum 7 kaliteli seçenek varsa kullanıcıya gösterir.
        - Kullanıcı 7 adet seçim yapar.
        - Seçimler Pazartesi'den Pazar'a kaydedilir.
        """

        week_start = self.db.get_next_monday().isoformat()

        self.db.clear_candidates(
            user_id=user_id,
            flow_type="weekly_bulk",
            day_name=None,
        )

        self.db.start_weekly_bulk_flow(user_id, week_start)

        candidates = self.recipe_search_tool.get_weekly_15_suggestions(
            user_id=user_id,
            db=self.db,
            context="weekly_bulk",
        )

        self.db.save_candidates(
            user_id=user_id,
            flow_type="weekly_bulk",
            day_name=None,
            candidates=candidates,
        )

        return self.recipe_search_tool.format_weekly_15_suggestions(candidates)

    def handle_weekly_bulk_selection(self, user_id: str, message: str) -> str:
        """
        Kullanıcıdan 7 seçim bekler.

        Kabul edilen format:
        1, 2, 3, 4, 5, 6, 7

        Bu seçimler sırasıyla:
        Pazartesi, Salı, Çarşamba, Perşembe, Cuma, Cumartesi, Pazar
        olarak kaydedilir.
        """

        flow = self.db.get_active_flow(user_id)

        if not flow or flow["flow_type"] != "weekly_bulk":
            return "Aktif haftalık plan seçim akışı yok. /haftalik_plan yazarak başlatabilirsin."

        numbers = self._parse_selection_numbers(message)

        if len(numbers) != 7:
            return (
                "Haftalık plan için tam 7 seçim yazmalısın."
                "Örnek:"
                "1, 2, 3, 4, 5, 6, 7"
            )

        if len(set(numbers)) != 7:
            return "Aynı yemeği haftada birden fazla seçmemek için 7 farklı numara yazmalısın."

        week_start = flow["week_start"]
        selected_items = []

        for day_name, option_no in zip(DAYS, numbers):
            item = self.db.get_candidate_by_option(
                user_id=user_id,
                flow_type="weekly_bulk",
                option_no=option_no,
                day_name=None,
            )

            if not item:
                return (
                    f"{option_no} numaralı seçeneği bulamadım."
                    "Lütfen listede görünen numaralardan 7 farklı seçim yaz."
                )

            self.db.save_weekly_plan_item(
                user_id=user_id,
                week_start=week_start,
                day_name=day_name,
                item=item,
            )

            selected_items.append({
                "day_name": day_name,
                "title": item["title"],
                "url": item.get("url", ""),
                "category": item.get("category", ""),
            })

        self.db.clear_active_flow(user_id)

        return "Haftalık plan kaydedildi." + self._format_selected_plan(selected_items)

    def _parse_selection_numbers(self, message: str) -> list:
        numbers = re.findall(r"\d+", message)
        return [int(n) for n in numbers]

    def _format_selected_plan(self, selected_items: list) -> str:
        lines = ["Haftalık akşam yemeği planı:", ""]

        for item in selected_items:
            lines.append(f"{item['day_name']}: [{item.get('category', '')}] {item['title']}")

            if item.get("url"):
                lines.append(item["url"])

        return "".join(lines)

    def show_weekly_plan(self, user_id: str, week_start: str | None = None) -> str:
        plan = self.db.get_weekly_plan(user_id, week_start)

        if not plan:
            return "Kayıtlı haftalık plan bulamadım. /haftalik_plan yazarak oluşturabilirsin."

        day_order = {day: idx for idx, day in enumerate(DAYS)}

        plan = sorted(
            plan,
            key=lambda x: day_order.get(x["day_name"], 99)
        )

        lines = ["Haftalık akşam yemeği planı:", ""]

        for item in plan:
            lines.append(f"{item['day_name']}: [{item.get('category', '')}] {item['title']}")

            if item.get("url"):
                lines.append(item["url"])

        return "".join(lines)
