class DailyChoiceTool:
    def __init__(self, db):
        self.db = db

    def save_daily_selection(self, user_id: str, option_no: int) -> str:
        item = self.db.get_candidate_by_option(
            user_id=user_id,
            flow_type="daily",
            option_no=option_no,
        )

        if not item:
            return "Bu seçim için aktif bir günlük öneri bulamadım. /bugun yazarak yeniden öneri alabilirsin."

        self.db.add_daily_choice(user_id, item)

        return f"Bugünkü yemek olarak kaydettim:\n{item['title']}\n{item.get('url', '')}"