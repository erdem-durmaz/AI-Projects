"""
Yemek Asistanı - FastAPI + Groq + SQLite
Kurulum: pip install fastapi uvicorn langchain-groq langgraph
Çalıştır: python app.py
"""

from dotenv import load_dotenv
import os, re, sqlite3, json, httpx
from pathlib import Path
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

GROQ_API_KEY   = os.environ.get("GROQ_API_KEY", "BURAYA_API_KEY_YAZ")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "BURAYA_TAVILY_KEY_YAZ")
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
"Ne yiyelim", "yemek öner", "akşam yemeği", "bugün ne yesek" gibi sorular geldiğinde SADECE şu JSON formatını döndür, başka hiçbir şey yazma.

ÇOK ÖNEMLİ: Her seferinde FARKLI yemekler öner. Bir önceki önerileri tekrar etme. Geniş bir Türk mutfağı repertuvarından seç — güveç, fırın, tencere, ızgara, çorba, pilav yemekleri, zeytinyağlılar, mevsim sebzeleri hepsi dahil. Yaratıcı ol.

{
  "type": "meal_suggestion",
  "categories": {
    "tavuk":      ["Yemek 1", "Yemek 2", "Yemek 3", "Yemek 4", "Yemek 5"],
    "dana_et":    ["Yemek 1", "Yemek 2", "Yemek 3", "Yemek 4", "Yemek 5"],
    "sebze":      ["Yemek 1", "Yemek 2", "Yemek 3", "Yemek 4", "Yemek 5"],
    "bakliyat":   ["Yemek 1", "Yemek 2", "Yemek 3", "Yemek 4", "Yemek 5"],
    "fit_salata": ["Yemek 1", "Yemek 2", "Yemek 3", "Yemek 4", "Yemek 5"],
    "balik":      ["Yemek 1", "Yemek 2", "Yemek 3", "Yemek 4", "Yemek 5"]
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


# ─── TAVILY ──────────────────────────────────────────────────────────────────

SEARCH_SITES = [
    "yemek.com",
    "nefisyemektarifleri.com",
    "lezzet.com.tr",
]

def tavily_search(query: str, max_results: int = 10) -> list:
    """Türk yemek sitelerinde arama yap."""
    # Boş query ise LLM'den rastgele yemek adı al
    if not query.strip():
        llm = ChatGroq(api_key=GROQ_API_KEY, model=MODEL_NAME, temperature=1.0, max_tokens=60)
        resp = llm.invoke([HumanMessage(content="Rastgele bir Türk akşam yemeği adı söyle, sadece ismi yaz.")])
        query = resp.content.strip().split("\n")[0]
        print(f"[search] Rastgele query: {query}")

    try:
        payload = {
            "api_key": TAVILY_API_KEY,
            "query": f"{query} tarifi",
            "max_results": max_results,
            "search_depth": "basic",
            "include_answer": False,
            "include_domains": SEARCH_SITES,
        }
        r = httpx.post("https://api.tavily.com/search", json=payload, timeout=12)
        data = r.json()

        raw_results = data.get("results", [])
        print(f"[search] Tavily döndürdü: {len(raw_results)} sonuç")
        for x in raw_results:
            print(f"  → {x.get('url','')[:80]} | {x.get('title','')[:50]}")

        results = []
        seen = set()

        for item in raw_results:
            title = item.get("title", "").strip()
            url   = item.get("url", "")

            # Yemek adını temizle
            clean = re.split(r"[|\-–]", title)[0].strip()
            clean = re.sub(r"(?i)(tarif[i]?|nasıl yapılır|yapılışı|malzemeleri).*$", "", clean).strip()
            clean = clean.strip(" ,.:")

            if len(clean) < 3 or clean.lower() in seen:
                continue

            seen.add(clean.lower())
            results.append({"name": clean, "url": url, "title": title})

        print(f"[search] Filtreleme sonrası: {len(results)} sonuç")
        return results

    except Exception as e:
        print(f"[search] Hata: {e}")
        return []

def fetch_page(url: str) -> dict:
    """URL'yi fetch et — liste sayfası mı tek tarif mi otomatik tespit et."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
            "Accept-Language": "tr-TR,tr;q=0.9",
        }
        r = httpx.get(url, headers=headers, timeout=12, follow_redirects=True)
        raw_html = r.text

        # HTML temizle
        clean_text = re.sub(r"<script[^>]*>.*?</script>", " ", raw_html, flags=re.DOTALL)
        clean_text = re.sub(r"<style[^>]*>.*?</style>", " ", clean_text, flags=re.DOTALL)
        clean_text = re.sub(r"<[^>]+>", " ", clean_text)
        clean_text = re.sub(r"\s+", " ", clean_text).strip()

        if len(clean_text) < 200:
            return {"type": "error", "error": "Sayfa içeriği okunamadı"}

        llm = ChatGroq(api_key=GROQ_API_KEY, model=MODEL_NAME, temperature=0.1, max_tokens=1200)
        prompt = f"""Aşağıdaki metin bir yemek sitesinden alınmıştır.

Önce sayfanın ne olduğuna karar ver:
- Eğer birden fazla yemek adı/listesi içeriyorsa → "list"
- Eğer tek bir yemeğin tarifi ise → "recipe"

"list" ise SADECE şu JSON formatında döndür:
{{
  "type": "list",
  "items": ["Yemek adı 1", "Yemek adı 2", "Yemek adı 3"]
}}

"recipe" ise SADECE şu JSON formatında döndür:
{{
  "type": "recipe",
  "name": "Yemeğin tam adı",
  "ingredients": ["miktar + malzeme 1", "miktar + malzeme 2"],
  "steps": ["adım 1", "adım 2"],
  "time": "süre (varsa)",
  "servings": "kaç kişilik (varsa)"
}}

Başka hiçbir şey yazma, sadece JSON döndür.

İçerik:
{clean_text[:4000]}"""

        result = llm.invoke([HumanMessage(content=prompt)]).content.strip()
        parsed = re.sub(r"```json|```", "", result).strip()
        data = json.loads(parsed)
        print(f"[fetch_page] type={data.get('type')} url={url[:60]}")
        return data

    except json.JSONDecodeError:
        return {"type": "error", "error": "İçerik ayrıştırılamadı"}
    except Exception as e:
        print(f"[fetch_page] Hata: {e}")
        return {"type": "error", "error": "Sayfa yüklenemedi"}

# ─── LANGGRAPH ───────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    messages: list
    response_text: str
    meal_data: dict

def call_llm(state: AgentState) -> AgentState:
    llm = ChatGroq(api_key=GROQ_API_KEY, model=MODEL_NAME, temperature=1.0, max_tokens=1500)
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


class SearchRequest(BaseModel):
    query: str = ""

class RecipeRequest(BaseModel):
    url: str

@app.post("/search")
def search_meals(req: SearchRequest):
    query = req.query or "sağlıklı Türk akşam yemeği"
    results = tavily_search(query)
    return {"results": results}

@app.post("/recipe")
def get_recipe(req: RecipeRequest):
    result = fetch_page(req.url)
    return {"result": result}


def slugify(name: str) -> str:
    tr_map = str.maketrans("çğışöüÇĞİŞÖÜ", "cgisoucgisoU")
    s = name.lower().translate(tr_map)
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s.strip())
    return s

def find_recipe_url(name: str) -> str | None:
    """Yemek adı için spesifik tarif URL'si bul — slug dene, sonra Tavily."""
    slug = slugify(name)
    headers = {"User-Agent": "Mozilla/5.0 Chrome/120"}
    candidates = [
        f"https://yemek.com/tarif/{slug}-tarifi/",
        f"https://yemek.com/tarif/{slug}/",
        f"https://www.nefisyemektarifleri.com/{slug}-tarifi",
        f"https://www.nefisyemektarifleri.com/{slug}",
        f"https://www.lezzet.com.tr/yemek-tarifleri/{slug}",
    ]
    for url in candidates:
        try:
            r = httpx.get(url, headers=headers, timeout=8, follow_redirects=True)
            if r.status_code == 200 and len(r.text) > 2000:
                print(f"[find_recipe_url] Bulundu: {r.url}")
                return str(r.url)
        except Exception:
            continue

    # Slug işe yaramadıysa Tavily ile spesifik ara
    try:
        r = httpx.post("https://api.tavily.com/search", json={
            "api_key": TAVILY_API_KEY,
            "query": f'"{name}" tarifi malzemeler yapılış',
            "max_results": 5,
            "include_domains": ["yemek.com", "nefisyemektarifleri.com", "lezzet.com.tr"],
        }, timeout=10)
        for item in r.json().get("results", []):
            url = item.get("url", "")
            # Sadece /tarif/ veya -tarifi içeren URL'ler
            if any(p in url for p in ["/tarif/", "-tarifi", "/yemek/"]):
                if not any(p in url for p in ["liste", "kategori", "haberler", "/fit-", "/diyet", "pratik-"]):
                    print(f"[find_recipe_url] Tavily buldu: {url}")
                    return url
    except Exception as e:
        print(f"[find_recipe_url] Tavily hata: {e}")
    return None

class RecipeByNameRequest(BaseModel):
    name: str

@app.post("/recipe_by_name")
def get_recipe_by_name(req: RecipeByNameRequest):
    print(f"[recipe_by_name] Aranan: {req.name}")
    url = find_recipe_url(req.name)
    if not url:
        return {"result": {"type": "error", "error": f"'{req.name}' için tarif sayfası bulunamadı"}}
    result = fetch_page(url)
    result["source_url"] = url
    return {"result": result}

if __name__ == "__main__":
    init_db()
    print("✅ http://localhost:8000 adresinde çalışıyor")
    if not TAVILY_API_KEY or TAVILY_API_KEY == "BURAYA_TAVILY_KEY_YAZ":
        print("⚠️  TAVILY_API_KEY ayarlanmamış — Keşfet sekmesi çalışmaz")
    uvicorn.run(app, host="127.0.0.1", port=8000)