import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import CATEGORY_META, CATEGORY_ORDER, DAYS, GOOGLE_API_KEY, STATIC_DIR, TAVILY_API_KEY
from app.db import (
    db_add_custom_recipe,
    db_add_favorite,
    db_clear_plan,
    db_delete_custom_recipe,
    db_find_custom_recipe_by_name,
    db_get_custom_recipe,
    db_get_favorites,
    db_get_plan,
    db_get_preferences,
    db_list_custom_recipes,
    db_remove_favorite,
    db_reorder_favorites,
    db_search_custom_recipes,
    db_add_plan_meal,
    db_clear_plan_day,
    db_remove_plan_meal,
    db_set_preferences,
    db_update_custom_recipe,
    init_db,
)
from app.llm import chat_completion, chat_stream, parse_meal_response
from app.models import (
    ChatRequest,
    CustomRecipeDeleteRequest,
    CustomRecipeRequest,
    CustomRecipeUpdateRequest,
    FavRequest,
    PlanClearDayRequest,
    PlanDayRequest,
    PreferencesRequest,
    RecipeByNameRequest,
    RecipeRequest,
    ReorderRequest,
    SearchRequest,
)
from app.search import fetch_page, find_recipe_url, tavily_search

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if not GOOGLE_API_KEY:
        logger.warning("GOOGLE_API_KEY is not set - chat will not work")
    if not TAVILY_API_KEY:
        logger.warning("TAVILY_API_KEY is not set — search will not work")
    yield


app = FastAPI(title="Yemek Asistanı", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def root():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(
            index,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
            },
        )
    raise HTTPException(status_code=404, detail="index.html not found")


@app.get("/manifest.json")
def manifest():
    path = STATIC_DIR / "manifest.json"
    if path.exists():
        return FileResponse(path, media_type="application/manifest+json")
    raise HTTPException(status_code=404)


@app.get("/sw.js")
def service_worker():
    path = STATIC_DIR / "sw.js"
    if path.exists():
        return FileResponse(
            path,
            media_type="application/javascript",
            headers={"Cache-Control": "no-cache"},
        )
    raise HTTPException(status_code=404)


def _enrich_meal_data(meal_data: dict) -> dict:
    enriched = {}
    keys = [k for k in CATEGORY_ORDER if k in meal_data] + [k for k in meal_data if k not in CATEGORY_ORDER]
    for key in keys:
        items = meal_data.get(key, [])
        if not items:
            continue
        meta = CATEGORY_META.get(key, {"label": key, "emoji": "🍽️", "color": "#f9fafb"})
        enriched[key] = {**meta, "items": items}
    return enriched


@app.post("/chat")
@limiter.limit("30/minute")
def chat(request: Request, req: ChatRequest):
    if not GOOGLE_API_KEY:
        raise HTTPException(status_code=503, detail="GOOGLE_API_KEY ayarlanmamış")
    prefs = db_get_preferences()
    code, parsed_data = chat_completion(req.message, req.history, prefs)
    if parsed_data:
        if code == "__MEAL__":
            return {"type": "meal", "data": _enrich_meal_data(parsed_data)}
        elif code == "__SEARCH__":
            return {"type": "action", "action": "open_recipe", "query": parsed_data["query"]}
    raise HTTPException(status_code=502, detail="Öneri oluşturulamadı, tekrar dene")


@app.post("/chat/stream")
@limiter.limit("30/minute")
def chat_stream_endpoint(request: Request, req: ChatRequest):
    if not GOOGLE_API_KEY:
        raise HTTPException(status_code=503, detail="GOOGLE_API_KEY ayarlanmamış")
    prefs = db_get_preferences()

    def generate():
        buffer = ""
        try:
            for token in chat_stream(req.message, req.history, prefs):
                buffer += token
                yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
            code, parsed_data = parse_meal_response(buffer)
            if not parsed_data:
                code, parsed_data = chat_completion(req.message, req.history, prefs)
            
            if parsed_data:
                if code == "__MEAL__":
                    payload = {"done": True, "type": "meal", "data": _enrich_meal_data(parsed_data)}
                elif code == "__SEARCH__":
                    payload = {"done": True, "type": "action", "action": "open_recipe", "query": parsed_data["query"]}
                else:
                    payload = {"done": True, "type": "error", "error": "Geçersiz format."}
            else:
                payload = {"done": True, "type": "error", "error": "Öneri oluşturulamadı, tekrar dene"}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.exception("Stream error: %s", e)
            yield f"data: {json.dumps({'error': 'Bir hata oluştu'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/favorites")
def get_favorites():
    return {"favorites": db_get_favorites()}


@app.post("/favorites/add")
def add_fav(req: FavRequest):
    db_add_favorite(req.name.strip())
    return {"favorites": db_get_favorites()}


@app.post("/favorites/remove")
def remove_fav(req: FavRequest):
    db_remove_favorite(req.name.strip())
    return {"favorites": db_get_favorites()}


@app.post("/favorites/reorder")
def reorder_favs(req: ReorderRequest):
    db_reorder_favorites(req.names)
    return {"ok": True}


@app.get("/plan")
def get_plan():
    return {"plan": db_get_plan(), "days": DAYS}


@app.post("/plan/add")
def add_plan_meal(req: PlanDayRequest):
    return {"plan": db_add_plan_meal(req.day, req.meal.strip())}


@app.post("/plan/remove")
def remove_plan_meal(req: PlanDayRequest):
    return {"plan": db_remove_plan_meal(req.day, req.meal.strip())}


@app.post("/plan/clear-day")
def clear_plan_day(req: PlanClearDayRequest):
    return {"plan": db_clear_plan_day(req.day)}


@app.post("/plan/clear")
def clear_plan():
    db_clear_plan()
    return {"plan": db_get_plan()}


@app.get("/preferences")
def get_preferences():
    return {"preferences": db_get_preferences()}


@app.post("/preferences")
def set_preferences(req: PreferencesRequest):
    db_set_preferences(req.model_dump())
    return {"preferences": db_get_preferences()}


def _custom_search_results(query: str) -> list[dict]:
    items = db_search_custom_recipes(query) if query.strip() else db_list_custom_recipes()
    return [
        {
            "name": item["name"],
            "url": f"custom://{item['id']}",
            "custom": True,
            "id": item["id"],
            "source": "Benim tarifim",
        }
        for item in items
    ]


@app.post("/search")
@limiter.limit("20/minute")
def search_meals(request: Request, req: SearchRequest):
    query = req.query.strip()
    custom = _custom_search_results(query)
    web_query = query or "sağlıklı Türk akşam yemeği"
    web = tavily_search(web_query)
    seen = {r["name"].lower() for r in custom}
    merged = custom + [r for r in web if r["name"].lower() not in seen]
    return {"results": merged}


@app.post("/recipe")
@limiter.limit("20/minute")
def get_recipe(request: Request, req: RecipeRequest):
    if req.url.startswith("custom://"):
        recipe_id = int(req.url.replace("custom://", ""))
        recipe = db_get_custom_recipe(recipe_id)
        if not recipe:
            return {"result": {"type": "error", "error": "Tarif bulunamadı"}}
        return {"result": recipe}
    return {"result": fetch_page(req.url)}


@app.post("/recipe_by_name")
@limiter.limit("20/minute")
def get_recipe_by_name(request: Request, req: RecipeByNameRequest):
    custom = db_find_custom_recipe_by_name(req.name.strip())
    if custom:
        return {"result": custom}
    url = find_recipe_url(req.name.strip())
    if not url:
        return {
            "result": {
                "type": "error",
                "error": f"'{req.name}' için tarif sayfası bulunamadı",
            }
        }
    result = fetch_page(url)
    result["source_url"] = url
    return {"result": result}


@app.get("/my-recipes")
def list_my_recipes():
    return {"recipes": db_list_custom_recipes()}


@app.get("/my-recipes/{recipe_id}")
def get_my_recipe(recipe_id: int):
    recipe = db_get_custom_recipe(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Tarif bulunamadı")
    return {"recipe": recipe}


@app.post("/my-recipes/add")
def add_my_recipe(req: CustomRecipeRequest):
    if not req.parsed_ingredients() and not req.parsed_steps():
        raise HTTPException(status_code=400, detail="En az malzeme veya yapılış adımı girin")
    try:
        recipe = db_add_custom_recipe(
            req.name,
            req.parsed_ingredients(),
            req.parsed_steps(),
            req.time,
            req.servings,
            req.notes,
        )
    except Exception as e:
        if "UNIQUE" in str(e):
            raise HTTPException(status_code=409, detail="Bu isimde bir tarif zaten var")
        raise
    return {"recipe": recipe, "recipes": db_list_custom_recipes()}


@app.post("/my-recipes/update")
def update_my_recipe(req: CustomRecipeUpdateRequest):
    if not req.parsed_ingredients() and not req.parsed_steps():
        raise HTTPException(status_code=400, detail="En az malzeme veya yapılış adımı girin")
    try:
        recipe = db_update_custom_recipe(
            req.id,
            req.name,
            req.parsed_ingredients(),
            req.parsed_steps(),
            req.time,
            req.servings,
            req.notes,
        )
    except Exception as e:
        if "UNIQUE" in str(e):
            raise HTTPException(status_code=409, detail="Bu isimde başka bir tarif var")
        raise
    if not recipe:
        raise HTTPException(status_code=404, detail="Tarif bulunamadı")
    return {"recipe": recipe, "recipes": db_list_custom_recipes()}


@app.post("/my-recipes/delete")
def delete_my_recipe(req: CustomRecipeDeleteRequest):
    if not db_delete_custom_recipe(req.id):
        raise HTTPException(status_code=404, detail="Tarif bulunamadı")
    return {"ok": True, "recipes": db_list_custom_recipes()}
