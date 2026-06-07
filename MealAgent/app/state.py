from typing import Optional, TypedDict, List, Dict, Any


class MealAgentState(TypedDict, total=False):
    user_id: str
    message: str
    intent: str
    response: str
    active_flow: Optional[Dict[str, Any]]
    candidates: List[Dict[str, Any]]