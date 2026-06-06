import sqlite3
from datetime import datetime

DB_PATH = "food_agent.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    """Tabloları oluştur (yoksa)"""
    conn = get_connection()
    cursor = conn.cursor()

    # Beğenilen yemekler tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,        -- fit, tatlı, pratik vs
            source_url TEXT,      -- tarif linki
            notes TEXT,           -- kullanıcı notu
            added_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # Haftalık plan tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weekly_plan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_start TEXT,      -- pazartesi tarihi
            day TEXT,             -- Pazartesi, Salı...
            meal_type TEXT,       -- kahvaltı, öğle, akşam
            meal_name TEXT,
            source_url TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Veritabanı hazır.")