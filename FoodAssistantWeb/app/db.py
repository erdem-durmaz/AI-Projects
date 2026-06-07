import json
import logging
from datetime import datetime, timedelta
from contextlib import contextmanager

from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DAYS, DEFAULT_PREFERENCES, RECIPE_CACHE_TTL_HOURS, DATABASE_URL

logger = logging.getLogger(__name__)

# SQLAlchemy setup
# For SQLite, check_same_thread=False is needed. For Postgres, it's not.
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Favorite(Base):
    __tablename__ = "favorites"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    position = Column(Integer, default=0)

class WeeklyPlan(Base):
    __tablename__ = "weekly_plan"
    day = Column(String, primary_key=True)
    meal = Column(Text, default="[]")

class Preference(Base):
    __tablename__ = "preferences"
    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)

class RecipeCache(Base):
    __tablename__ = "recipe_cache"
    url = Column(String, primary_key=True)
    data = Column(Text, nullable=False)
    fetched_at = Column(String, nullable=False)

class CustomRecipe(Base):
    __tablename__ = "custom_recipes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    ingredients = Column(Text, nullable=False, default="[]")
    steps = Column(Text, nullable=False, default="[]")
    time = Column(String, default="")
    servings = Column(String, default="")
    notes = Column(Text, default="")
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)

@contextmanager
def db_session():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
    with db_session() as db:
        # Initialize DAYS
        for day in DAYS:
            if not db.query(WeeklyPlan).filter(WeeklyPlan.day == day).first():
                db.add(WeeklyPlan(day=day, meal="[]"))
        
        # Initialize Preferences
        for key, value in DEFAULT_PREFERENCES.items():
            if not db.query(Preference).filter(Preference.key == key).first():
                db.add(Preference(key=key, value=value))
                
        # Migrate old plan format
        plans = db.query(WeeklyPlan).all()
        for p in plans:
            raw = p.meal or ""
            if not raw.startswith("["):
                p.meal = json.dumps([raw], ensure_ascii=False) if raw else "[]"
    logger.info(f"Database initialized at {DATABASE_URL}")

def db_get_favorites() -> list[str]:
    with db_session() as db:
        favs = db.query(Favorite).order_by(Favorite.position.asc(), Favorite.id.desc()).all()
        return [f.name for f in favs]

def db_add_favorite(name: str):
    with db_session() as db:
        existing = db.query(Favorite).filter(Favorite.name == name).first()
        if not existing:
            from sqlalchemy.sql import func
            max_pos = db.query(func.max(Favorite.position)).scalar() or 0
            db.add(Favorite(name=name, position=max_pos + 1))

def db_remove_favorite(name: str):
    with db_session() as db:
        fav = db.query(Favorite).filter(Favorite.name == name).first()
        if fav:
            db.delete(fav)

def db_reorder_favorites(names: list):
    with db_session() as db:
        for i, name in enumerate(names):
            fav = db.query(Favorite).filter(Favorite.name == name).first()
            if fav:
                fav.position = i

def _parse_plan_meals(raw: str) -> list[str]:
    if not raw:
        return []
    if raw.startswith("["):
        try:
            data = json.loads(raw)
            return [m for m in data if isinstance(m, str) and m.strip()] if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []
    return [raw]

def db_get_plan() -> dict[str, list[str]]:
    with db_session() as db:
        plans = db.query(WeeklyPlan).all()
        return {p.day: _parse_plan_meals(p.meal) for p in plans}

def db_add_plan_meal(day: str, meal: str) -> dict[str, list[str]]:
    meal = meal.strip()
    if not meal:
        return db_get_plan()
    with db_session() as db:
        plan = db.query(WeeklyPlan).filter(WeeklyPlan.day == day).first()
        if plan:
            meals = _parse_plan_meals(plan.meal)
            if meal not in meals:
                meals.append(meal)
                plan.meal = json.dumps(meals, ensure_ascii=False)
    return db_get_plan()

def db_remove_plan_meal(day: str, meal: str) -> dict[str, list[str]]:
    meal = meal.strip()
    with db_session() as db:
        plan = db.query(WeeklyPlan).filter(WeeklyPlan.day == day).first()
        if plan:
            meals = [m for m in _parse_plan_meals(plan.meal) if m != meal]
            plan.meal = json.dumps(meals, ensure_ascii=False)
    return db_get_plan()

def db_clear_plan_day(day: str) -> dict[str, list[str]]:
    with db_session() as db:
        plan = db.query(WeeklyPlan).filter(WeeklyPlan.day == day).first()
        if plan:
            plan.meal = "[]"
    return db_get_plan()

def db_clear_plan():
    with db_session() as db:
        db.query(WeeklyPlan).update({WeeklyPlan.meal: "[]"})

def db_get_preferences() -> dict[str, str]:
    with db_session() as db:
        prefs_db = db.query(Preference).all()
    prefs = dict(DEFAULT_PREFERENCES)
    prefs.update({p.key: p.value for p in prefs_db})
    return prefs

def db_set_preferences(prefs: dict[str, str]):
    with db_session() as db:
        for key, value in prefs.items():
            if key in DEFAULT_PREFERENCES:
                p = db.query(Preference).filter(Preference.key == key).first()
                if p:
                    p.value = value
                else:
                    db.add(Preference(key=key, value=value))

def db_get_cached_recipe(url: str) -> dict | None:
    cutoff = datetime.utcnow() - timedelta(hours=RECIPE_CACHE_TTL_HOURS)
    with db_session() as db:
        row = db.query(RecipeCache).filter(RecipeCache.url == url).first()
        if not row:
            return None
        try:
            fetched = datetime.fromisoformat(row.fetched_at)
            if fetched < cutoff:
                return None
            return json.loads(row.data)
        except ValueError:
            return None

def db_set_cached_recipe(url: str, data: dict):
    with db_session() as db:
        row = db.query(RecipeCache).filter(RecipeCache.url == url).first()
        if row:
            row.data = json.dumps(data, ensure_ascii=False)
            row.fetched_at = datetime.utcnow().isoformat()
        else:
            db.add(RecipeCache(
                url=url,
                data=json.dumps(data, ensure_ascii=False),
                fetched_at=datetime.utcnow().isoformat()
            ))

def _normalize_name(name: str) -> str:
    tr_map = str.maketrans("çğışöüÇĞİŞÖÜ", "cgisoucgisou")
    return name.lower().translate(tr_map).strip()

def _recipe_to_dict(r: CustomRecipe) -> dict:
    return {
        "type": "recipe",
        "id": r.id,
        "name": r.name,
        "ingredients": json.loads(r.ingredients),
        "steps": json.loads(r.steps),
        "time": r.time or "",
        "servings": r.servings or "",
        "notes": r.notes or "",
        "custom": True,
    }

def _recipe_to_summary(r: CustomRecipe) -> dict:
    ingredients = json.loads(r.ingredients)
    steps = json.loads(r.steps)
    return {
        "id": r.id,
        "name": r.name,
        "time": r.time or "",
        "servings": r.servings or "",
        "ingredient_count": len(ingredients),
        "step_count": len(steps),
        "updated_at": r.updated_at,
    }

def db_list_custom_recipes() -> list[dict]:
    with db_session() as db:
        from sqlalchemy.sql.expression import func
        rows = db.query(CustomRecipe).order_by(func.lower(CustomRecipe.name)).all()
        return [_recipe_to_summary(r) for r in rows]

def db_get_custom_recipe(recipe_id: int) -> dict | None:
    with db_session() as db:
        r = db.query(CustomRecipe).filter(CustomRecipe.id == recipe_id).first()
        return _recipe_to_dict(r) if r else None

def db_find_custom_recipe_by_name(name: str) -> dict | None:
    target = _normalize_name(name)
    with db_session() as db:
        rows = db.query(CustomRecipe).all()
        exact = [r for r in rows if _normalize_name(r.name) == target]
        if len(exact) >= 1:
            return _recipe_to_dict(exact[0])
        partial = [r for r in rows if target in _normalize_name(r.name)]
        if len(partial) == 1:
            return _recipe_to_dict(partial[0])
        return None

def db_search_custom_recipes(query: str) -> list[dict]:
    q = _normalize_name(query)
    if not q:
        return db_list_custom_recipes()
    results = []
    with db_session() as db:
        rows = db.query(CustomRecipe).all()
        for item in rows:
            if q in _normalize_name(item.name):
                results.append(_recipe_to_summary(item))
    results.sort(key=lambda x: x["name"].lower())
    return results

def db_add_custom_recipe(
    name: str,
    ingredients: list[str],
    steps: list[str],
    time: str = "",
    servings: str = "",
    notes: str = "",
) -> dict:
    now = datetime.utcnow().isoformat()
    with db_session() as db:
        recipe = CustomRecipe(
            name=name.strip(),
            ingredients=json.dumps(ingredients, ensure_ascii=False),
            steps=json.dumps(steps, ensure_ascii=False),
            time=time.strip(),
            servings=servings.strip(),
            notes=notes.strip(),
            created_at=now,
            updated_at=now
        )
        db.add(recipe)
        db.flush()
        return _recipe_to_dict(recipe)

def db_update_custom_recipe(
    recipe_id: int,
    name: str,
    ingredients: list[str],
    steps: list[str],
    time: str = "",
    servings: str = "",
    notes: str = "",
) -> dict | None:
    now = datetime.utcnow().isoformat()
    with db_session() as db:
        recipe = db.query(CustomRecipe).filter(CustomRecipe.id == recipe_id).first()
        if not recipe:
            return None
        recipe.name = name.strip()
        recipe.ingredients = json.dumps(ingredients, ensure_ascii=False)
        recipe.steps = json.dumps(steps, ensure_ascii=False)
        recipe.time = time.strip()
        recipe.servings = servings.strip()
        recipe.notes = notes.strip()
        recipe.updated_at = now
        db.flush()
        return _recipe_to_dict(recipe)

def db_delete_custom_recipe(recipe_id: int) -> bool:
    with db_session() as db:
        recipe = db.query(CustomRecipe).filter(CustomRecipe.id == recipe_id).first()
        if recipe:
            db.delete(recipe)
            return True
        return False
