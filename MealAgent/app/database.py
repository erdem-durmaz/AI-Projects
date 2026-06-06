import os
import json
import sqlite3
from datetime import datetime, date, timedelta


class Database:
    def __init__(self, path: str):
        self.path = path
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)

    def connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.connect() as conn:
            cur = conn.cursor()

            cur.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id TEXT PRIMARY KEY,
                people_count INTEGER,
                meal_type TEXT,
                criteria TEXT,
                exclusions TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                title TEXT,
                url TEXT,
                category TEXT,
                created_at TEXT
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS daily_choices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                choice_date TEXT,
                title TEXT,
                url TEXT,
                category TEXT,
                created_at TEXT
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS weekly_plan (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                week_start TEXT,
                day_name TEXT,
                title TEXT,
                url TEXT,
                category TEXT,
                created_at TEXT,
                UNIQUE(user_id, week_start, day_name)
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS recipe_candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                flow_type TEXT,
                day_name TEXT,
                option_no INTEGER,
                title TEXT,
                url TEXT,
                category TEXT,
                source TEXT,
                created_at TEXT
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS active_flow (
                user_id TEXT PRIMARY KEY,
                flow_type TEXT,
                current_day_index INTEGER,
                week_start TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS last_selected (
                user_id TEXT PRIMARY KEY,
                title TEXT,
                url TEXT,
                category TEXT,
                updated_at TEXT
            )
            """)

            conn.commit()

    def ensure_default_preferences(self, user_id: str):
        now = datetime.now().isoformat()
        criteria = [
            "hafif",
            "fit",
            "pratik",
            "düşük kalorili",
            "proteinli",
            "glutensiz",
            "ev yemeği",
            "sebze ağırlıklı",
            "tavuk ağırlıklı",
            "dana eti ağırlıklı",
            "fırın yemeği",
            "tencere yemeği",
        ]
        exclusions = ["kuzu eti", "uzakdoğu mutfağı"]

        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT user_id FROM user_preferences WHERE user_id = ?", (user_id,))
            exists = cur.fetchone()

            if not exists:
                cur.execute("""
                INSERT INTO user_preferences
                (user_id, people_count, meal_type, criteria, exclusions, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    3,
                    "akşam",
                    json.dumps(criteria, ensure_ascii=False),
                    json.dumps(exclusions, ensure_ascii=False),
                    now,
                    now,
                ))
                conn.commit()

    def get_preferences(self, user_id: str):
        self.ensure_default_preferences(user_id)
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM user_preferences WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            return dict(row)

    def clear_candidates(self, user_id: str, flow_type: str, day_name: str | None = None):
        with self.connect() as conn:
            if day_name:
                conn.execute(
                    "DELETE FROM recipe_candidates WHERE user_id = ? AND flow_type = ? AND day_name = ?",
                    (user_id, flow_type, day_name)
                )
            else:
                conn.execute(
                    "DELETE FROM recipe_candidates WHERE user_id = ? AND flow_type = ?",
                    (user_id, flow_type)
                )
            conn.commit()

    def save_candidates(self, user_id: str, flow_type: str, day_name: str | None, candidates: list):
        now = datetime.now().isoformat()
        self.clear_candidates(user_id, flow_type, day_name)

        with self.connect() as conn:
            for item in candidates:
                conn.execute("""
                INSERT INTO recipe_candidates
                (user_id, flow_type, day_name, option_no, title, url, category, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    flow_type,
                    day_name,
                    int(item["option_no"]),
                    item["title"],
                    item.get("url", ""),
                    item.get("category", ""),
                    item.get("source", ""),
                    now,
                ))
            conn.commit()

    def get_candidate_by_option(self, user_id: str, flow_type: str, option_no: int, day_name: str | None = None):
        with self.connect() as conn:
            if day_name:
                row = conn.execute("""
                SELECT * FROM recipe_candidates
                WHERE user_id = ? AND flow_type = ? AND day_name = ? AND option_no = ?
                """, (user_id, flow_type, day_name, option_no)).fetchone()
            else:
                row = conn.execute("""
                SELECT * FROM recipe_candidates
                WHERE user_id = ? AND flow_type = ? AND option_no = ?
                """, (user_id, flow_type, option_no)).fetchone()

            return dict(row) if row else None

    def set_last_selected(self, user_id: str, title: str, url: str, category: str):
        now = datetime.now().isoformat()
        with self.connect() as conn:
            conn.execute("""
            INSERT INTO last_selected (user_id, title, url, category, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                title = excluded.title,
                url = excluded.url,
                category = excluded.category,
                updated_at = excluded.updated_at
            """, (user_id, title, url, category, now))
            conn.commit()

    def get_last_selected(self, user_id: str):
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM last_selected WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            return dict(row) if row else None

    def add_daily_choice(self, user_id: str, item: dict):
        now = datetime.now().isoformat()
        today = date.today().isoformat()

        with self.connect() as conn:
            conn.execute("""
            INSERT INTO daily_choices
            (user_id, choice_date, title, url, category, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                today,
                item["title"],
                item.get("url", ""),
                item.get("category", ""),
                now,
            ))
            conn.commit()

        self.set_last_selected(
            user_id,
            item["title"],
            item.get("url", ""),
            item.get("category", "")
        )

    def add_favorite(self, user_id: str, title: str, url: str, category: str):
        now = datetime.now().isoformat()
        with self.connect() as conn:
            conn.execute("""
            INSERT INTO favorites (user_id, title, url, category, created_at)
            VALUES (?, ?, ?, ?, ?)
            """, (user_id, title, url, category, now))
            conn.commit()

    def list_favorites(self, user_id: str):
        with self.connect() as conn:
            rows = conn.execute("""
            SELECT * FROM favorites
            WHERE user_id = ?
            ORDER BY id DESC
            """, (user_id,)).fetchall()
            return [dict(r) for r in rows]

    def get_recent_meals(self, user_id: str, limit: int = 10):
        with self.connect() as conn:
            rows = conn.execute("""
            SELECT title FROM daily_choices
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """, (user_id, limit)).fetchall()
            return [r["title"] for r in rows]

    def start_weekly_flow(self, user_id: str, week_start: str):
        now = datetime.now().isoformat()
        with self.connect() as conn:
            conn.execute("""
            INSERT INTO active_flow
            (user_id, flow_type, current_day_index, week_start, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                flow_type = excluded.flow_type,
                current_day_index = excluded.current_day_index,
                week_start = excluded.week_start,
                updated_at = excluded.updated_at
            """, (user_id, "weekly_plan", 0, week_start, now, now))
            conn.commit()

    def get_active_flow(self, user_id: str):
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM active_flow WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            return dict(row) if row else None

    def update_weekly_flow_day_index(self, user_id: str, day_index: int):
        now = datetime.now().isoformat()
        with self.connect() as conn:
            conn.execute("""
            UPDATE active_flow
            SET current_day_index = ?, updated_at = ?
            WHERE user_id = ?
            """, (day_index, now, user_id))
            conn.commit()

    def clear_active_flow(self, user_id: str):
        with self.connect() as conn:
            conn.execute("DELETE FROM active_flow WHERE user_id = ?", (user_id,))
            conn.commit()

    def get_next_monday(self):
        today = date.today()
        days_ahead = 0 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return today + timedelta(days=days_ahead)

    def save_weekly_plan_item(self, user_id: str, week_start: str, day_name: str, item: dict):
        now = datetime.now().isoformat()
        with self.connect() as conn:
            conn.execute("""
            INSERT INTO weekly_plan
            (user_id, week_start, day_name, title, url, category, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, week_start, day_name) DO UPDATE SET
                title = excluded.title,
                url = excluded.url,
                category = excluded.category,
                created_at = excluded.created_at
            """, (
                user_id,
                week_start,
                day_name,
                item["title"],
                item.get("url", ""),
                item.get("category", ""),
                now,
            ))
            conn.commit()

        self.set_last_selected(
            user_id,
            item["title"],
            item.get("url", ""),
            item.get("category", "")
        )

    def get_weekly_plan(self, user_id: str, week_start: str | None = None):
        if week_start is None:
            week_start = self.get_next_monday().isoformat()

        with self.connect() as conn:
            rows = conn.execute("""
            SELECT * FROM weekly_plan
            WHERE user_id = ? AND week_start = ?
            ORDER BY id ASC
            """, (user_id, week_start)).fetchall()
            return [dict(r) for r in rows]