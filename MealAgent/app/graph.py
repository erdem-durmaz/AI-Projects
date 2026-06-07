from langgraph.graph import StateGraph, START, END

from app.state import MealAgentState
from app.tools.recipe_search import RecipeSearchTool
from app.tools.favorites import FavoritesTool
from app.tools.daily_choice import DailyChoiceTool
from app.tools.weekly_plan import WeeklyPlanTool
from app.tools.preferences import PreferencesTool


class MealAgentGraph:
    def __init__(self, db):
        self.db = db

        self.recipe_search = RecipeSearchTool()
        self.favorites = FavoritesTool(db)
        self.daily_choice = DailyChoiceTool(db)
        self.weekly_plan = WeeklyPlanTool(db, self.recipe_search)
        self.preferences = PreferencesTool(db)

        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(MealAgentState)

        builder.add_node("router", self._router_node)
        builder.add_node("action", self._action_node)

        builder.add_edge(START, "router")
        builder.add_edge("router", "action")
        builder.add_edge("action", END)

        return builder.compile()

    def invoke(self, user_id: str, message: str) -> str:
        self.db.ensure_default_preferences(user_id)

        result = self.graph.invoke({
            "user_id": user_id,
            "message": message,
        })

        return result.get("response", "Bir cevap oluşturamadım.")

    def _looks_like_weekly_bulk_selection(self, message: str) -> bool:
        import re
        numbers = re.findall(r"\d+", message)
        return len(numbers) >= 7

    def _router_node(self, state: MealAgentState) -> MealAgentState:
        message = state["message"].strip().lower()
        user_id = state["user_id"]
        active_flow = self.db.get_active_flow(user_id)

        intent = "general"

        if message in ["/start", "start"]:
            intent = "start"

        elif message in ["/bugun", "bugün", "bugun", "bugün ne yiyelim"]:
            intent = "daily_suggestion"

        elif message in ["/haftalik_plan", "/haftalık_plan", "haftalık plan", "bu hafta plan yap"]:
            intent = "weekly_plan_start"

        elif message in ["/plan", "planı göster", "haftalık planı göster"]:
            intent = "show_weekly_plan"

        elif message in ["/favoriler", "favoriler", "favorilerimi göster", "favorilerimi listele"]:
            intent = "list_favorites"

        elif "favorilere ekle" in message or "favoriye ekle" in message:
            intent = "add_favorite"

        elif message in ["/ayarlar", "ayarlar", "tercihler"]:
            intent = "show_preferences"

        elif message in ["/iptal", "iptal", "vazgeç"]:
            intent = "cancel"

        elif self._looks_like_weekly_bulk_selection(message):
            if active_flow and active_flow["flow_type"] == "weekly_bulk":
                intent = "weekly_bulk_selection"
            else:
                intent = "general"

        elif message in ["1", "2", "3", "4", "5"]:
            if active_flow and active_flow["flow_type"] == "daily":
                intent = "daily_selection"
            elif active_flow and active_flow["flow_type"] == "weekly_bulk":
                intent = "weekly_bulk_selection"
            else:
                intent = "no_active_selection"

        elif "yemek konuşmayalım" in message or "yemek konusunu kapat" in message:
            intent = "stop_food_topic"

        state["intent"] = intent
        state["active_flow"] = active_flow
        return state

    def _action_node(self, state: MealAgentState) -> MealAgentState:
        user_id = state["user_id"]
        message = state["message"].strip()
        intent = state["intent"]

        if intent == "start":
            response = (
                "Merhaba. Yemek planlama asistanın hazırım.\n\n"
                "Komutlar:\n"
                "/bugun - Bugün için 5 farklı kategoriden yemek önerisi\n"
                "/haftalik_plan - Haftalık akşam yemeği planı için seçenek listesi\n"
                "/plan - Haftalık planı göster\n"
                "/favoriler - Favorileri listele\n"
                "/ayarlar - Tercihleri göster\n"
                "/iptal - Aktif akışı iptal et"
            )

        elif intent == "daily_suggestion":
            self.db.clear_active_flow(user_id)
            self.db.start_daily_flow(user_id)

            candidates = self.recipe_search.get_five_category_suggestions(
                user_id=user_id,
                db=self.db,
                day_name=None,
                context="daily",
            )

            self.db.save_candidates(
                user_id=user_id,
                flow_type="daily",
                day_name=None,
                candidates=candidates,
            )

            response = self.recipe_search.format_suggestions(
                title="Bugün için 5 farklı kategoriden seçenek:",
                candidates=candidates,
            )

        elif intent == "daily_selection":
            try:
                option_no = int(message)
                response = self.daily_choice.save_daily_selection(user_id, option_no)
            except Exception:
                response = "Seçim için 1, 2, 3, 4 veya 5 yazmalısın."

        elif intent == "weekly_plan_start":
            self.db.clear_active_flow(user_id)
            response = self.weekly_plan.start_weekly_plan(user_id)

        elif intent == "weekly_bulk_selection":
            response = self.weekly_plan.handle_weekly_bulk_selection(user_id, message)

        elif intent == "show_weekly_plan":
            response = self.weekly_plan.show_weekly_plan(user_id)

        elif intent == "list_favorites":
            response = self.favorites.list_favorites(user_id)

        elif intent == "add_favorite":
            response = self.favorites.add_last_selected_to_favorites(user_id)

        elif intent == "show_preferences":
            response = self.preferences.show_preferences(user_id)

        elif intent == "cancel":
            self.db.clear_active_flow(user_id)
            response = "Aktif akışı iptal ettim."

        elif intent == "no_active_selection":
            response = (
                "Aktif bir seçim akışı bulamadım.\n\n"
                "Günlük öneri almak için /bugun yazabilirsin.\n"
                "Haftalık plan oluşturmak için /haftalik_plan yazabilirsin."
            )

        elif intent == "stop_food_topic":
            response = "Tamam, yemek konusunu kapatalım. Başka bir konuda yardımcı olabilirim."

        else:
            response = (
                "Bunu yemek planlama komutu olarak algılamadım.\n\n"
                "Kullanabileceğin komutlar:\n"
                "/bugun\n"
                "/haftalik_plan\n"
                "/plan\n"
                "/favoriler\n"
                "/ayarlar"
            )

        state["response"] = response
        return state
