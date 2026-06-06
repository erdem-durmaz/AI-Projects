from typing import TypedDict, Annotated
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
import operator
load_dotenv()
from pathlib import Path
load_dotenv(Path(__file__).parent / ".env")  # agent.py'nin yanındaki .env'i zorla
from langchain_ollama import ChatOllama

from tools import search_recipes, add_favorite, list_favorites, create_weekly_plan, get_weekly_plan, suggest_meals_for_plan, save_selected_meals

# --- STATE ---

class AgentState(TypedDict):
    messages: Annotated[list, operator.add]  # mesaj geçmişi birikir

# --- MODEL & TOOLS ---

tools = [search_recipes, add_favorite, list_favorites, create_weekly_plan, get_weekly_plan, suggest_meals_for_plan, save_selected_meals]

# GROQ (rate limit dolunca comment'le)
"""
from langchain_groq import ChatGroq
model = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.7
).bind_tools(tools)
"""

# OLLAMA (groq kilitlenince bunu aç, üsttekileri comment'le)
model = ChatOllama(
     model="llama3.1:8b",
     base_url="http://localhost:11434",
     temperature=0.7).bind_tools(tools)


SYSTEM_PROMPT = """Sen bir yemek asistanısın. Türkçe konuşuyorsun.

Kullanabileceğin araçlar:
- search_recipes: yemek tarifi aramak için
- add_favorite: yemeği favorilere eklemek için
- list_favorites: favorileri listelemek için
- suggest_meals_for_plan: haftalık plan için yemek önermek için
- save_selected_meals: seçilen numaraları plana kaydetmek için
- get_weekly_plan: mevcut planı göstermek için

KURAL: Kullanıcı "plan öner" veya "haftalık plan" dediğinde suggest_meals_for_plan aracını çağır.
KURAL: Kullanıcı "1,3,5" gibi numara yazdığında save_selected_meals aracını çağır.
KURAL: Asla araç çağırmadan kendi kendine liste oluşturma.
KURAL: Araçtan gelen sonucu aynen ilet."""

# --- NODES ---

def agent_node(state: AgentState):
    """LLM karar verir: yanıt mı verecek, tool mu çağıracak?"""
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = model.invoke(messages)
    return {"messages": [response]}


def should_continue(state: AgentState):
    """Tool call var mı? Varsa tools node'a git, yoksa bitir."""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END



# --- GRAPH ---

tool_node = ToolNode(tools)

graph = StateGraph(AgentState)

graph.add_node("agent", agent_node)
graph.add_node("tools", tool_node)

graph.set_entry_point("agent")

graph.add_conditional_edges(
    "agent",
    should_continue,
    {"tools": "tools", END: END}
)

# Tool çalıştıktan sonra tekrar agent'a dön (sonucu yorumlasın)
graph.add_edge("tools", "agent")

food_agent = graph.compile()