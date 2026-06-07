import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta

from app.config import DAYS, DB_PATH, DEFAULT_PREFERENCES, RECIPE_CACHE_TTL_HOURS

logger = logging.getLogger(__name__)


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                position INTEGER DEFAULT 0
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS weekly_plan (
                day TEXT PRIMARY KEY,
                meal TEXT DEFAULT ''
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS recipe_cache (
                url TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                fetched_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS custom_recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                ingredients TEXT NOT NULL DEFAULT '[]',
                steps TEXT NOT NULL DEFAULT '[]',
                time TEXT DEFAULT '',
                servings TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )"""
        )
        for day in DAYS:
            conn.execute(
                "INSERT OR IGNORE INTO weekly_plan (day, meal) VALUES (?, '[]')",
                (day,),
            )
        _migrate_plan_rows(conn)
        for key, value in DEFAULT_PREFERENCES.items():
            conn.execute(
                "INSERT OR IGNORE INTO preferences (key, value) VALUES (?, ?)",
                (key, value),
            )
    logger.info("Database initialized at %s", DB_PATH)


def db_get_favorites() -> list[str]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT name FROM favorites ORDER BY position ASC, id DESC"
        ).fetchall()
    return [r["name"] for r in rows]


def db_add_favorite(name: str):
    with get_db() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO favorites (name, position)
               VALUES (?, (SELECT COALESCE(MAX(position), 0) + 1 FROM favorites))""",
            (name,),
        )


def db_remove_favorite(name: str):
    with get_db() as conn:
        conn.execute("DELETE FROM favorites WHERE name = ?", (name,))


def db_reorder_favorites(names: list):
    with get_db() as conn:
        for i, name in enumerate(names):
            conn.execute(
                "UPDATE favorites SET position = ? WHERE name = ?",
                (i, name),
            )


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


def _migrate_plan_rows(conn: sqlite3.Connection):
    rows = conn.execute("SELECT day, meal FROM weekly_plan").fetchall()
    for row in rows:
        raw = row["meal"] or ""
        if raw.startswith("["):
            continue
        new_val = json.dumps([raw], ensure_ascii=False) if raw else "[]"
        conn.execute(
            "UPDATE weekly_plan SET meal = ? WHERE day = ?",
            (new_val, row["day"]),
        )


def db_get_plan() -> dict[str, list[str]]:
    with get_db() as conn:
        rows = conn.execute("SELECT day, meal FROM weekly_plan").fetchall()
    return {r["day"]: _parse_plan_meals(r["meal"]) for r in rows}


def db_add_plan_meal(day: str, meal: str) -> dict[str, list[str]]:
    meal = meal.strip()
    if not meal:
        return db_get_plan()
    plan = db_get_plan()
    meals = list(plan.get(day, []))
    if meal not in meals:
        meals.append(meal)
    with get_db() as conn:
        conn.execute(
            "UPDATE weekly_plan SET meal = ? WHERE day = ?",
            (json.dumps(meals, ensure_ascii=False), day),
        )
    return db_get_plan()


def db_remove_plan_meal(day: str, meal: str) -> dict[str, list[str]]:
    meal = meal.strip()
    plan = db_get_plan()
    meals = [m for m in plan.get(day, []) if m != meal]
    with get_db() as conn:
        conn.execute(
            "UPDATE weekly_plan SET meal = ? WHERE day = ?",
            (json.dumps(meals, ensure_ascii=False), day),
        )
    return db_get_plan()


def db_clear_plan_day(day: str) -> dict[str, list[str]]:
    with get_db() as conn:
        conn.execute("UPDATE weekly_plan SET meal = '[]' WHERE day = ?", (day,))
    return db_get_plan()


def db_clear_plan():
    with get_db() as conn:
        conn.execute("UPDATE weekly_plan SET meal = '[]'")


def db_get_preferences() -> dict[str, str]:
    with get_db() as conn:
        rows = conn.execute("SELECT key, value FROM preferences").fetchall()
    prefs = dict(DEFAULT_PREFERENCES)
    prefs.update({r["key"]: r["value"] for r in rows})
    return prefs


def db_set_preferences(prefs: dict[str, str]):
    with get_db() as conn:
        for key, value in prefs.items():
            if key in DEFAULT_PREFERENCES:
                conn.execute(
                    """INSERT INTO preferences (key, value) VALUES (?, ?)
                       ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
                    (key, value),
                )


def db_get_cached_recipe(url: str) -> dict | None:
    cutoff = datetime.utcnow() - timedelta(hours=RECIPE_CACHE_TTL_HOURS)
    with get_db() as conn:
        row = conn.execute(
            "SELECT data, fetched_at FROM recipe_cache WHERE url = ?",
            (url,),
        ).fetchone()
    if not row:
        return None
    try:
        fetched = datetime.fromisoformat(row["fetched_at"])
    except ValueError:
        return None
    if fetched < cutoff:
        return None
    return json.loads(row["data"])


def db_set_cached_recipe(url: str, data: dict):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO recipe_cache (url, data, fetched_at) VALUES (?, ?, ?)
               ON CONFLICT(url) DO UPDATE SET
                 data = excluded.data,
                 fetched_at = excluded.fetched_at""",
            (url, json.dumps(data, ensure_ascii=False), datetime.utcnow().isoformat()),
        )


def _normalize_name(name: str) -> str:
    tr_map = str.maketrans("çğışöüÇĞİŞÖÜ", "cgisoucgisou")
    return name.lower().translate(tr_map).strip()


def _row_to_recipe(row: sqlite3.Row) -> dict:
    return {
        "type": "recipe",
        "id": row["id"],
        "name": row["name"],
        "ingredients": json.loads(row["ingredients"]),
        "steps": json.loads(row["steps"]),
        "time": row["time"] or "",
        "servings": row["servings"] or "",
        "notes": row["notes"] or "",
        "custom": True,
    }


def _row_to_summary(row: sqlite3.Row) -> dict:
    ingredients = json.loads(row["ingredients"])
    steps = json.loads(row["steps"])
    return {
        "id": row["id"],
        "name": row["name"],
        "time": row["time"] or "",
        "servings": row["servings"] or "",
        "ingredient_count": len(ingredients),
        "step_count": len(steps),
        "updated_at": row["updated_at"],
    }


def db_list_custom_recipes() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM custom_recipes ORDER BY name COLLATE NOCASE ASC"
        ).fetchall()
    return [_row_to_summary(r) for r in rows]


def db_get_custom_recipe(recipe_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM custom_recipes WHERE id = ?",
            (recipe_id,),
        ).fetchone()
    return _row_to_recipe(row) if row else None


def db_find_custom_recipe_by_name(name: str) -> dict | None:
    target = _normalize_name(name)
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM custom_recipes").fetchall()
    exact = [r for r in rows if _normalize_name(r["name"]) == target]
    if len(exact) == 1:
        return _row_to_recipe(exact[0])
    if len(exact) > 1:
        return _row_to_recipe(exact[0])
    partial = [r for r in rows if target in _normalize_name(r["name"])]
    if len(partial) == 1:
        return _row_to_recipe(partial[0])
    return None


def db_search_custom_recipes(query: str) -> list[dict]:
    q = _normalize_name(query)
    if not q:
        return db_list_custom_recipes()
    results = []
    for item in db_list_custom_recipes():
        if q in _normalize_name(item["name"]):
            results.append(item)
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
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO custom_recipes
               (name, ingredients, steps, time, servings, notes, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                name.strip(),
                json.dumps(ingredients, ensure_ascii=False),
                json.dumps(steps, ensure_ascii=False),
                time.strip(),
                servings.strip(),
                notes.strip(),
                now,
                now,
            ),
        )
        recipe_id = cur.lastrowid
    return db_get_custom_recipe(recipe_id)


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
    with get_db() as conn:
        cur = conn.execute(
            """UPDATE custom_recipes
               SET name = ?, ingredients = ?, steps = ?, time = ?, servings = ?,
                   notes = ?, updated_at = ?
               WHERE id = ?""",
            (
                name.strip(),
                json.dumps(ingredients, ensure_ascii=False),
                json.dumps(steps, ensure_ascii=False),
                time.strip(),
                servings.strip(),
                notes.strip(),
                now,
                recipe_id,
            ),
        )
        if cur.rowcount == 0:
            return None
    return db_get_custom_recipe(recipe_id)


def db_delete_custom_recipe(recipe_id: int) -> bool:
    with get_db() as conn:
        cur = conn.execute("DELETE FROM custom_recipes WHERE id = ?", (recipe_id,))
    return cur.rowcount > 0
