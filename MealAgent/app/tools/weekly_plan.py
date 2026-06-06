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
        week_start = self.db.get_next_monday().isoformat()
        self.db.start_weekly_flow(user_id, week_start)

        return self._send_day_options(user_id, day_index=0)

    def handle_weekly_selection(self, user_id: str, option_no: int) -> str:
        flow = self.db.get_active_flow(user_id)

        if not flow or flow["flow_type"] != "weekly_plan":
            return "Aktif haftalık plan akışı yok. /haftalik_plan yazarak başlatabilirsin."

        day_index = int(flow["current_day_index"])
        week_start = flow["week_start"]
        day_name = DAYS[day_index]

        item = self.db.get_candidate_by_option(
            user_id=user_id,
            flow_type="weekly_plan",
            day_name=day_name,
            option_no=option_no,
        )

        if not item:
            return f"{day_name} için bu seçeneği bulamadım. Lütfen 1-5 arasında seçim yap."

        self.db.save_weekly_plan_item(
            user_id=user_id,
            week_start=week_start,
            day_name=day_name,
            item=item,
        )

        next_index = day_index + 1

        if next_index >= len(DAYS):
            self.db.clear_active_flow(user_id)
            return "Haftalık plan tamamlandı.\n\n" + self.show_weekly_plan(user_id, week_start)

        self.db.update_weekly_flow_day_index(user_id, next_index)
        return self._send_day_options(user_id, day_index=next_index)

    def _send_day_options(self, user_id: str, day_index: int) -> str:
        day_name = DAYS[day_index]

        candidates = self.recipe_search_tool.get_five_category_suggestions(
            user_id=user_id,
            db=self.db,
            day_name=day_name,
            context="weekly_plan",
        )

        self.db.save_candidates(
            user_id=user_id,
            flow_type="weekly_plan",
            day_name=day_name,
            candidates=candidates,
        )

        return self.recipe_search_tool.format_suggestions(
            title=f"{day_name} için 5 farklı kategoriden seçenek:",
            candidates=candidates,
        )

    def show_weekly_plan(self, user_id: str, week_start: str | None = None) -> str:
        plan = self.db.get_weekly_plan(user_id, week_start)

        if not plan:
            return "Kayıtlı haftalık plan bulamadım. /haftalik_plan yazarak oluşturabilirsin."

        lines = ["Haftalık akşam yemeği planı:", ""]

        for item in plan:
            lines.append(f"{item['day_name']}: [{item.get('category', '')}] {item['title']}")
            if item.get("url"):
                lines.append(item["url"])

        return "\n".join(lines)