import sqlite3
from datetime import datetime

DB_PATH = "food_agent.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    """Tabloları oluştur (yoksa)"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            source_url TEXT,
            notes TEXT,
            added_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weekly_plan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_start TEXT,
            day TEXT,
            meal_type TEXT,
            meal_name TEXT,
            source_url TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meal_suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            meal_name TEXT,
            source_url TEXT,
            suggested_at TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Veritabanı hazır.")