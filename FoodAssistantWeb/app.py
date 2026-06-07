"""
Yemek Asistanı - FastAPI + Groq + SQLite
Kurulum: pip install fastapi uvicorn langchain-groq langgraph
Çalıştır: python app.py
"""

import os, re, sqlite3, json
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
import uvicorn
load_dotenv()

# ─── CONFIG ──────────────────────────────────────────────────────────────────

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "BURAYA_API_KEY_YAZ")
MODEL_NAME   = "llama-3.3-70b-versatile"
DB_PATH      = Path(__file__).parent / "favorites.db"

DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]

SYSTEM_PROMPT = """Sen yardımsever bir Türk yemek asistanısın.

VARSAYILAN TERCİHLER:
- Kişi sayısı: 3
- Öğün: Akşam yemeği
- Tarz: Ev yemeği (pratik, hafif, fit)
- Tercihler: Düşük kalorili, proteinli, glutensiz, sebze ağırlıklı, tavuk veya dana eti, fırın veya tencere yemekleri

KESİNLİKLE ÖNERİLMEYECEKLER:
- Kuzu eti, Uzakdoğu mutfağı, Noodle, Soya sosu, Teriyaki, Sushi, Ramen, Wok tarzı yemekler

YEMEK ÖNERİSİ KURALLARI:
"Ne yiyelim", "yemek öner", "akşam yemeği", "bugün ne yesek" gibi sorular geldiğinde SADECE şu JSON formatını döndür, başka hiçbir şey yazma:

{
  "type": "meal_suggestion",
  "categories": {
    "tavuk":      ["Yemek 1", "Yemek 2", "Yemek 3"],
    "dana_et":    ["Yemek 1", "Yemek 2", "Yemek 3"],
    "sebze":      ["Yemek 1", "Yemek 2", "Yemek 3"],
    "bakliyat":   ["Yemek 1", "Yemek 2", "Yemek 3"],
    "fit_salata": ["Yemek 1", "Yemek 2", "Yemek 3"],
    "balik":      ["Yemek 1", "Yemek 2", "Yemek 3"]
  }
}

Yemekle ilgili OLMAYAN sorularda normal, yardımsever bir asistan olarak Türkçe cevap ver. JSON kullanma.
"""

CATEGORY_META = {
    "tavuk":      {"label": "Tavuk",        "emoji": "🍗", "color": "#fff7ed"},
    "dana_et":    {"label": "Dana / Et",    "emoji": "🥩", "color": "#fef2f2"},
    "sebze":      {"label": "Sebze",        "emoji": "🥦", "color": "#f0fdf4"},
    "bakliyat":   {"label": "Bakliyat",     "emoji": "🫘", "color": "#fefce8"},
    "fit_salata": {"label": "Fit & Salata", "emoji": "🥗", "color": "#f0f9ff"},
    "balik":      {"label": "Balık",        "emoji": "🐟", "color": "#fdf4ff"},
}

# ─── DATABASE ────────────────────────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        position INTEGER DEFAULT 0
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS weekly_plan (
        day TEXT PRIMARY KEY,
        meal TEXT DEFAULT ''
    )""")
    # Günleri önceden doldur
    for day in DAYS:
        conn.execute("INSERT OR IGNORE INTO weekly_plan (day, meal) VALUES (?, '')", (day,))
    conn.commit(); conn.close()

def db_get_favorites():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT name FROM favorites ORDER BY position ASC, id DESC").fetchall()
    conn.close()
    return [r[0] for r in rows]

def db_add_favorite(name: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT OR IGNORE INTO favorites (name, position) VALUES (?, (SELECT COALESCE(MAX(position),0)+1 FROM favorites))", (name,))
    conn.commit(); conn.close()

def db_remove_favorite(name: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM favorites WHERE name = ?", (name,))
    conn.commit(); conn.close()

def db_reorder_favorites(names: list):
    conn = sqlite3.connect(DB_PATH)
    for i, name in enumerate(names):
        conn.execute("UPDATE favorites SET position = ? WHERE name = ?", (i, name))
    conn.commit(); conn.close()

def db_get_plan():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT day, meal FROM weekly_plan").fetchall()
    conn.close()
    return {r[0]: r[1] for r in rows}

def db_set_plan_day(day: str, meal: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE weekly_plan SET meal = ? WHERE day = ?", (meal, day))
    conn.commit(); conn.close()

def db_clear_plan():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE weekly_plan SET meal = ''")
    conn.commit(); conn.close()

# ─── LANGGRAPH ───────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    messages: list
    response_text: str
    meal_data: dict

def call_llm(state: AgentState) -> AgentState:
    llm = ChatGroq(api_key=GROQ_API_KEY, model=MODEL_NAME, temperature=0.7, max_tokens=1024)
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    raw = llm.invoke(messages).content.strip()
    meal_data = None
    try:
        clean = re.sub(r"```json|```", "", raw).strip()
        parsed = json.loads(clean)
        if parsed.get("type") == "meal_suggestion":
            meal_data = parsed["categories"]
            raw = "__MEAL__"
    except Exception:
        pass
    return {**state, "response_text": raw, "meal_data": meal_data}

graph = (lambda: (lambda g: (g.add_node("llm", call_llm), g.set_entry_point("llm"), g.add_edge("llm", END), g.compile())[-1])(StateGraph(AgentState)))()

# ─── FASTAPI ─────────────────────────────────────────────────────────────────

app = FastAPI()

class ChatRequest(BaseModel):
    message: str
    history: list = []

class FavRequest(BaseModel):
    name: str

class ReorderRequest(BaseModel):
    names: list

class PlanDayRequest(BaseModel):
    day: str
    meal: str

@app.get("/", response_class=HTMLResponse)
def root():
    return FileResponse(Path(__file__).parent / "index.html")

@app.post("/chat")
def chat(req: ChatRequest):
    lc_messages = []
    for msg in req.history:
        if msg["role"] == "user":
            lc_messages.append(HumanMessage(content=msg["content"]))
        else:
            lc_messages.append(AIMessage(content=msg["content"]))
    lc_messages.append(HumanMessage(content=req.message))
    result = graph.invoke({"messages": lc_messages, "response_text": "", "meal_data": None})
    if result["meal_data"]:
        enriched = {}
        for key, items in result["meal_data"].items():
            meta = CATEGORY_META.get(key, {"label": key, "emoji": "🍽️", "color": "#f9fafb"})
            enriched[key] = {**meta, "items": items}
        return {"type": "meal", "data": enriched}
    return {"type": "text", "text": result["response_text"]}

@app.get("/favorites")
def get_favorites():
    return {"favorites": db_get_favorites()}

@app.post("/favorites/add")
def add_fav(req: FavRequest):
    db_add_favorite(req.name)
    return {"favorites": db_get_favorites()}

@app.post("/favorites/remove")
def remove_fav(req: FavRequest):
    db_remove_favorite(req.name)
    return {"favorites": db_get_favorites()}

@app.post("/favorites/reorder")
def reorder_favs(req: ReorderRequest):
    db_reorder_favorites(req.names)
    return {"ok": True}

@app.get("/plan")
def get_plan():
    return {"plan": db_get_plan(), "days": DAYS}

@app.post("/plan/set")
def set_plan_day(req: PlanDayRequest):
    db_set_plan_day(req.day, req.meal)
    return {"plan": db_get_plan()}

@app.post("/plan/clear")
def clear_plan():
    db_clear_plan()
    return {"plan": db_get_plan()}

if __name__ == "__main__":
    init_db()
    print("✅ http://localhost:8000 adresinde çalışıyor")
    uvicorn.run(app, host="127.0.0.1", port=8000)
