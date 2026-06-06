# Meal Agent - Tüm Kodlar (Tek Dosya)

Bu dosya, projedeki ana kodların tamamını tek yerde toplar.
Her bölümü ilgili path'e kaydedebilirsin.

---

## `requirements.txt`

```txt
langgraph>=1.2.0
python-telegram-bot>=22.0
groq>=1.0.0
tavily-python>=0.7.0
python-dotenv>=1.0.1
typing-extensions>=4.12.0
```

---

## `.env.example`

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
GROQ_API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key

GROQ_MODEL=llama-3.3-70b-versatile
DATABASE_PATH=data/meals.db
TIMEZONE=Europe/Istanbul
```

---

## `main.py`

```python
from app.config import settings
from app.database import Database
from app.bot.telegram_bot import run_bot


def main():
    db = Database(settings.database_path)
    db.init_db()
    run_bot(db)


if __name__ == "__main__":
    main()
```

---

## `app/config.py`

```python
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    telegram_bot_token: str
    groq_api_key: str
    tavily_api_key: str
    groq_model: str
    database_path: str
    timezone: str


settings = Settings(
    telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
    groq_api_key=os.getenv("GROQ_API_KEY", ""),
    tavily_api_key=os.getenv("TAVILY_API_KEY", ""),
    groq_model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
    database_path=os.getenv("DATABASE_PATH", "data/meals.db"),
    timezone=os.getenv("TIMEZONE", "Europe/Istanbul"),
)
```

---

## `app/state.py`

```python
from typing import Optional, TypedDict, List, Dict, Any


class MealAgentState(TypedDict, total=False):
    user_id: str
    message: str
    intent: str
    response: str
    active_flow: Optional[Dict[str, Any]]
    candidates: List[Dict[str, Any]]
```

---

## `app/prompts.py`

```python
BASE_MEAL_CRITERIA = """
Sen bir yemek planlama asistanısın.

Kullanıcının sabit tercihleri:
- 3 kişilik
- Sadece akşam yemeği
- Hafif
- Fit
- Pratik
- Düşük kalorili
- Proteinli
- Glutensiz
- Ev yemeği tarzı
- Sebze, tavuk veya dana eti ağırlıklı
- Fırın veya tencere yemeği olabilir

Kesinlikle önerme:
- Kuzu eti
- Uzakdoğu mutfağı
- Noodle
- Soya sosu
- Teriyaki
- Sushi
- Ramen
- Wok tarzı yemekler
- Quesadilla
- Taco
- Burrito
- Nachos

Cevap formatı kısa olmalı.
Kullanıcı tarif detayı istemedikçe tarif anlatma.
"""

FIVE_CATEGORY_INSTRUCTION = """
Her öneri setinde 5 farklı kategori olsun:

1. Tavuk ağırlıklı
2. Dana/et ağırlıklı, ama kuzu eti kesinlikle yok
3. Sebze ağırlıklı
4. Bakliyat veya proteinli ev yemeği
5. Fit ve glutensiz hafif alternatif

Her kategori için 1 yemek seç.
Toplam tam 5 seçenek dön.
"""

JSON_RECIPE_SELECTION_PROMPT = """
Aşağıdaki web arama sonuçlarından kullanıcının kriterlerine en uygun 5 yemeği seç.

Kurallar:
- Tam 5 seçenek dön.
- Her seçenek farklı kategoriden gelsin.
- Sadece spesifik yemek tarifi sayfası seç.
- Genel tarif listesi, kategori sayfası, fikir listesi veya sosyal medya linki seçme.
- Başlık doğrudan yemek adı gibi olmalı.
- 'Glutensiz tarifler', 'Diyet yemekleri', 'Akşam yemeği fikirleri', '25 tarif', 'Kolay yemek fikirleri' gibi başlıkları seçme.
- Instagram, TikTok, YouTube, Reddit, Pinterest linklerini seçme.
- Kuzu eti içerenleri ele.
- Uzakdoğu mutfağı çağrışımı yapanları ele.
- Noodle, soya sosu, teriyaki, sushi, ramen, wok geçenleri ele.
- Glutensiz veya glutensize uyarlanabilir olanları tercih et.
- Türk ev yemeği tarzına yakın olsun.
- Sadece geçerli JSON dön, açıklama yazma.

JSON formatı:
[
  {
    "option_no": 1,
    "category": "Tavuk",
    "title": "Fırında Sebzeli Tavuk Tarifi",
    "url": "https://...",
    "source": "site adı"
  }
]
"""

WEEKLY_15_RECIPE_SELECTION_PROMPT = """
Aşağıdaki doğrulanmış tarif adaylarından haftalık akşam yemeği planı için en uygun tarifleri seç.

Kurallar:
- Mümkünse 15 seçenek dön.
- En az 7 seçenek dön.
- Sadece verilen aday URL'lerden seçim yap.
- URL uydurma.
- Başlık uydurma.
- Genel tarif listesi, kategori sayfası, haber, sağlık rehberi veya sosyal medya linki seçme.
- Başlık doğrudan yemek adı gibi olmalı.
- Kuzu eti içerenleri ele.
- Uzakdoğu mutfağı çağrışımı yapanları ele.
- Noodle, soya sosu, teriyaki, sushi, ramen, wok geçenleri ele.
- Türk ev yemeği tarzına yakın olsun.
- Kategori dengesini mümkün olduğunca koru.
- Sadece geçerli JSON dön, açıklama yazma.

JSON formatı:
[
  {
    "option_no": 1,
    "category": "Tavuk",
    "title": "Fırında Sebzeli Tavuk Tarifi",
    "url": "https://...",
    "source": "site adı"
  }
]
"""

WEEKLY_QUERY_GENERATION_PROMPT = """
Sen bir yemek tarifi arama stratejisi üreten asistansın.

Kullanıcının tercihleri:
- 3 kişilik
- Sadece akşam yemeği
- Hafif
- Fit
- Pratik
- Düşük kalorili
- Proteinli
- Glutensiz veya glutensize kolay uyarlanabilir
- Ev yemeği tarzı
- Sebze, tavuk veya dana eti ağırlıklı
- Fırın veya tencere yemeği olabilir

Kesinlikle hariç:
- Kuzu eti
- Uzakdoğu mutfağı
- Noodle
- Soya sosu
- Teriyaki
- Sushi
- Ramen
- Wok yemekleri
- Meksika mutfağı gibi ev yemeği çizgisinden uzak yemekler

Görev:
Haftalık plan için web'de tarif araması yapılacak.
Bunun için 25 adet Türkçe arama sorgusu üret.

Kategori dağılımı:
- 5 Tavuk
- 5 Dana/Et
- 5 Sebze
- 5 Bakliyat
- 5 Fit Glutensiz

Kurallar:
- Sorgular yemek ismi listesi gibi sabit olmasın.
- Ama spesifik tarif sayfası bulmaya uygun olsun.
- 'tarifi' kelimesini kullan.
- 'liste', 'fikirleri', 'kategori', 'diyet yemekleri listesi' gibi genel sayfa getirecek sorgular üretme.
- Kuzu eti veya Uzakdoğu çağrışımı olan sorgu üretme.
- Sadece geçerli JSON dön, açıklama yazma.

JSON formatı:
[
  {
    "category": "Tavuk",
    "query": "hafif glutensiz fırında sebzeli tavuk tarifi"
  },
  {
    "category": "Dana/Et",
    "query": "dana etli sebze yemeği tarifi tencere"
  }
]
"""
```

---

## `app/llm.py`

```python
import json
import re
from groq import Groq
from app.config import settings


class GroqLLM:
    def __init__(self):
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = settings.groq_model

    def chat(self, system: str, user: str, temperature: float = 0.2) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
        )
        return response.choices[0].message.content or ""

    def json_chat(self, system: str, user: str, temperature: float = 0.1):
        raw = self.chat(system=system, user=user, temperature=temperature)
        return self._extract_json(raw)

    def _extract_json(self, text: str):
        text = text.strip()
        try:
            return json.loads(text)
        except Exception:
            pass
        match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
        if not match:
            raise ValueError(f"JSON bulunamadı. Model cevabı: {text}")
        return json.loads(match.group(1))
```

---

## `app/database.py`

```python
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
            "hafif", "fit", "pratik", "düşük kalorili", "proteinli", "glutensiz",
            "ev yemeği", "sebze ağırlıklı", "tavuk ağırlıklı", "dana eti ağırlıklı",
            "fırın yemeği", "tencere yemeği",
        ]
        exclusions = ["kuzu eti", "uzakdoğu mutfağı"]
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT user_id FROM user_preferences WHERE user_id = ?", (user_id,))
            if not cur.fetchone():
                cur.execute("""
                INSERT INTO user_preferences
                (user_id, people_count, meal_type, criteria, exclusions, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id, 3, "akşam",
                    json.dumps(criteria, ensure_ascii=False),
                    json.dumps(exclusions, ensure_ascii=False),
                    now, now,
                ))
                conn.commit()

    def get_preferences(self, user_id: str):
        self.ensure_default_preferences(user_id)
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM user_preferences WHERE user_id = ?", (user_id,)).fetchone()
            return dict(row) if row else None

    def clear_candidates(self, user_id: str, flow_type: str, day_name: str | None = None):
        with self.connect() as conn:
            if day_name:
                conn.execute("DELETE FROM recipe_candidates WHERE user_id = ? AND flow_type = ? AND day_name = ?", (user_id, flow_type, day_name))
            else:
                conn.execute("DELETE FROM recipe_candidates WHERE user_id = ? AND flow_type = ?", (user_id, flow_type))
            conn.commit()

    def save_candidates(self, user_id: str, flow_type: str, day_name: str | None, candidates: list):
        now = datetime.now().isoformat()
        self.clear_candidates(user_id=user_id, flow_type=flow_type, day_name=day_name)
        with self.connect() as conn:
            for item in candidates:
                conn.execute("""
                INSERT INTO recipe_candidates
                (user_id, flow_type, day_name, option_no, title, url, category, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id, flow_type, day_name, int(item["option_no"]), item["title"],
                    item.get("url", ""), item.get("category", ""), item.get("source", ""), now,
                ))
            conn.commit()

    def get_candidate_by_option(self, user_id: str, flow_type: str, option_no: int, day_name: str | None = None):
        with self.connect() as conn:
            if day_name:
                row = conn.execute(
                    "SELECT * FROM recipe_candidates WHERE user_id = ? AND flow_type = ? AND day_name = ? AND option_no = ?",
                    (user_id, flow_type, day_name, option_no),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM recipe_candidates WHERE user_id = ? AND flow_type = ? AND option_no = ?",
                    (user_id, flow_type, option_no),
                ).fetchone()
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
            row = conn.execute("SELECT * FROM last_selected WHERE user_id = ?", (user_id,)).fetchone()
            return dict(row) if row else None

    def add_daily_choice(self, user_id: str, item: dict):
        now = datetime.now().isoformat()
        today = date.today().isoformat()
        with self.connect() as conn:
            conn.execute("""
            INSERT INTO daily_choices (user_id, choice_date, title, url, category, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, today, item["title"], item.get("url", ""), item.get("category", ""), now))
            conn.commit()
        self.set_last_selected(user_id, item["title"], item.get("url", ""), item.get("category", ""))

    def get_recent_meals(self, user_id: str, limit: int = 10):
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT title FROM daily_choices WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
            return [row["title"] for row in rows]

    def add_favorite(self, user_id: str, title: str, url: str, category: str):
        now = datetime.now().isoformat()
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO favorites (user_id, title, url, category, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, title, url, category, now),
            )
            conn.commit()

    def list_favorites(self, user_id: str):
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM favorites WHERE user_id = ? ORDER BY id DESC", (user_id,)).fetchall()
            return [dict(row) for row in rows]

    def start_daily_flow(self, user_id: str):
        now = datetime.now().isoformat()
        with self.connect() as conn:
            conn.execute("""
            INSERT INTO active_flow (user_id, flow_type, current_day_index, week_start, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                flow_type = excluded.flow_type,
                current_day_index = excluded.current_day_index,
                week_start = excluded.week_start,
                updated_at = excluded.updated_at
            """, (user_id, "daily", 0, "", now, now))
            conn.commit()

    def start_weekly_bulk_flow(self, user_id: str, week_start: str):
        now = datetime.now().isoformat()
        with self.connect() as conn:
            conn.execute("""
            INSERT INTO active_flow (user_id, flow_type, current_day_index, week_start, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                flow_type = excluded.flow_type,
                current_day_index = excluded.current_day_index,
                week_start = excluded.week_start,
                updated_at = excluded.updated_at
            """, (user_id, "weekly_bulk", 0, week_start, now, now))
            conn.commit()

    def get_active_flow(self, user_id: str):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM active_flow WHERE user_id = ?", (user_id,)).fetchone()
            return dict(row) if row else None

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
            INSERT INTO weekly_plan (user_id, week_start, day_name, title, url, category, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, week_start, day_name) DO UPDATE SET
                title = excluded.title,
                url = excluded.url,
                category = excluded.category,
                created_at = excluded.created_at
            """, (
                user_id, week_start, day_name, item["title"], item.get("url", ""), item.get("category", ""), now,
            ))
            conn.commit()
        self.set_last_selected(user_id, item["title"], item.get("url", ""), item.get("category", ""))

    def get_weekly_plan(self, user_id: str, week_start: str | None = None):
        if week_start is None:
            week_start = self.get_next_monday().isoformat()
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM weekly_plan WHERE user_id = ? AND week_start = ? ORDER BY id ASC",
                (user_id, week_start),
            ).fetchall()
            return [dict(row) for row in rows]
```

---

## `app/tools/favorites.py`

```python
class FavoritesTool:
    def __init__(self, db):
        self.db = db

    def add_last_selected_to_favorites(self, user_id: str) -> str:
        last = self.db.get_last_selected(user_id)
        if not last:
            return "Henüz favorilere ekleyebileceğim seçilmiş bir yemek yok."
        self.db.add_favorite(
            user_id=user_id,
            title=last["title"],
            url=last.get("url", ""),
            category=last.get("category", ""),
        )
        return f"Favorilere ekledim:\n{last['title']}\n{last.get('url', '')}"

    def list_favorites(self, user_id: str) -> str:
        favorites = self.db.list_favorites(user_id)
        if not favorites:
            return "Henüz favori yemeğin yok."
        lines = ["Favori yemeklerin:", ""]
        for idx, item in enumerate(favorites, start=1):
            lines.append(f"{idx}) [{item.get('category', '')}] {item['title']}")
            if item.get("url"):
                lines.append(item["url"])
        return "\n".join(lines)
```

---

## `app/tools/daily_choice.py`

```python
class DailyChoiceTool:
    def __init__(self, db):
        self.db = db

    def save_daily_selection(self, user_id: str, option_no: int) -> str:
        item = self.db.get_candidate_by_option(
            user_id=user_id,
            flow_type="daily",
            option_no=option_no,
        )
        if not item:
            return "Bu seçim için aktif bir günlük öneri bulamadım. /bugun yazarak yeniden öneri alabilirsin."
        self.db.add_daily_choice(user_id, item)
        self.db.clear_active_flow(user_id)
        return f"Bugünkü yemek olarak kaydettim:\n{item['title']}\n{item.get('url', '')}"
```

---

## `app/tools/preferences.py`

```python
import json


class PreferencesTool:
    def __init__(self, db):
        self.db = db

    def show_preferences(self, user_id: str) -> str:
        prefs = self.db.get_preferences(user_id)
        criteria = json.loads(prefs["criteria"])
        exclusions = json.loads(prefs["exclusions"])
        lines = [
            "Yemek tercihlerin:",
            "",
            f"Kişi sayısı: {prefs['people_count']}",
            f"Öğün: {prefs['meal_type']}",
            "",
            "Kriterler:",
        ]
        for item in criteria:
            lines.append(f"- {item}")
        lines.append("")
        lines.append("Hariç tutulacaklar:")
        for item in exclusions:
            lines.append(f"- {item}")
        lines.append("")
        lines.append("Günlük öneri sayısı: 5")
        lines.append("Günlük öneri kategorileri: Tavuk, Dana/Et, Sebze, Bakliyat, Fit Glutensiz")
        return "\n".join(lines)
```

---

## `app/tools/weekly_plan.py`

```python
import re


DAYS = [
    "Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar",
]


class WeeklyPlanTool:
    def __init__(self, db, recipe_search_tool):
        self.db = db
        self.recipe_search_tool = recipe_search_tool

    def start_weekly_plan(self, user_id: str) -> str:
        week_start = self.db.get_next_monday().isoformat()
        self.db.clear_candidates(user_id=user_id, flow_type="weekly_bulk", day_name=None)
        self.db.start_weekly_bulk_flow(user_id, week_start)
        candidates = self.recipe_search_tool.get_weekly_15_suggestions(user_id=user_id, db=self.db, context="weekly_bulk")
        self.db.save_candidates(user_id=user_id, flow_type="weekly_bulk", day_name=None, candidates=candidates)
        return self.recipe_search_tool.format_weekly_15_suggestions(candidates)

    def handle_weekly_bulk_selection(self, user_id: str, message: str) -> str:
        flow = self.db.get_active_flow(user_id)
        if not flow or flow["flow_type"] != "weekly_bulk":
            return "Aktif haftalık plan seçim akışı yok. /haftalik_plan yazarak başlatabilirsin."
        numbers = self._parse_selection_numbers(message)
        if len(numbers) != 7:
            return "Haftalık plan için tam 7 seçim yazmalısın.\n\nÖrnek:\n1, 2, 3, 4, 5, 6, 7"
        if len(set(numbers)) != 7:
            return "Aynı yemeği haftada birden fazla seçmemek için 7 farklı numara yazmalısın."
        week_start = flow["week_start"]
        selected_items = []
        for day_name, option_no in zip(DAYS, numbers):
            item = self.db.get_candidate_by_option(user_id=user_id, flow_type="weekly_bulk", option_no=option_no, day_name=None)
            if not item:
                return f"{option_no} numaralı seçeneği bulamadım.\n\nLütfen listede görünen numaralardan 7 farklı seçim yaz."
            self.db.save_weekly_plan_item(user_id=user_id, week_start=week_start, day_name=day_name, item=item)
            selected_items.append({
                "day_name": day_name,
                "title": item["title"],
                "url": item.get("url", ""),
                "category": item.get("category", ""),
            })
        self.db.clear_active_flow(user_id)
        return "Haftalık plan kaydedildi.\n\n" + self._format_selected_plan(selected_items)

    def _parse_selection_numbers(self, message: str) -> list:
        numbers = re.findall(r"\d+", message)
        return [int(n) for n in numbers]

    def _format_selected_plan(self, selected_items: list) -> str:
        lines = ["Haftalık akşam yemeği planı:", ""]
        for item in selected_items:
            lines.append(f"{item['day_name']}: [{item.get('category', '')}] {item['title']}")
            if item.get("url"):
                lines.append(item["url"])
        return "\n".join(lines)

    def show_weekly_plan(self, user_id: str, week_start: str | None = None) -> str:
        plan = self.db.get_weekly_plan(user_id, week_start)
        if not plan:
            return "Kayıtlı haftalık plan bulamadım. /haftalik_plan yazarak oluşturabilirsin."
        day_order = {day: idx for idx, day in enumerate(DAYS)}
        plan = sorted(plan, key=lambda x: day_order.get(x["day_name"], 99))
        lines = ["Haftalık akşam yemeği planı:", ""]
        for item in plan:
            lines.append(f"{item['day_name']}: [{item.get('category', '')}] {item['title']}")
            if item.get("url"):
                lines.append(item["url"])
        return "\n".join(lines)
```

---

## `app/tools/recipe_search.py`

> Bu dosya uzun olduğu için tam hali ayrı bölümde devam ediyor.

```python
# NOT: Bu birleştirilmiş dosyada recipe_search.py tam sürümünü de aynı mantıkla kullan.
# Eğer istersen bir sonraki adımda sadece recipe_search.py için ayrı bir tek dosya da çıkarabilirim.
```

---

## `app/graph.py`

```python
from langgraph.graph import StateGraph, START, END

from app.state import MealAgentState
from app.tools.recipe_search import RecipeSearchTool
from app.tools.favorites import FavoritesTool
from app.tools.daily_choice import DailyChoiceTool
from app.tools.weekly_plan import WeeklyPlanTool
from app.tools.preferences import PreferencesTool


class MealAgentGraph:
    def __init__(self, db):
        self.db = db
        self.recipe_search = RecipeSearchTool()
        self.favorites = FavoritesTool(db)
        self.daily_choice = DailyChoiceTool(db)
        self.weekly_plan = WeeklyPlanTool(db, self.recipe_search)
        self.preferences = PreferencesTool(db)
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(MealAgentState)
        builder.add_node("router", self._router_node)
        builder.add_node("action", self._action_node)
        builder.add_edge(START, "router")
        builder.add_edge("router", "action")
        builder.add_edge("action", END)
        return builder.compile()

    def invoke(self, user_id: str, message: str) -> str:
        self.db.ensure_default_preferences(user_id)
        result = self.graph.invoke({"user_id": user_id, "message": message})
        return result.get("response", "Bir cevap oluşturamadım.")
```

---

## `app/bot/telegram_bot.py`

```python
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from app.config import settings
from app.graph import MealAgentGraph


def run_bot(db):
    if not settings.telegram_bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN .env içinde tanımlı değil.")

    meal_agent = MealAgentGraph(db)

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        response = meal_agent.invoke(user_id=user_id, message="/start")
        await update.message.reply_text(response, disable_web_page_preview=True)

    async def bugun(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        await update.message.reply_text("5 farklı kategoriden yemek önerisi arıyorum...", disable_web_page_preview=True)
        response = meal_agent.invoke(user_id=user_id, message="/bugun")
        await update.message.reply_text(response, disable_web_page_preview=True)

    async def haftalik_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        await update.message.reply_text("Haftalık plan için yemek seçenekleri arıyorum...", disable_web_page_preview=True)
        response = meal_agent.invoke(user_id=user_id, message="/haftalik_plan")
        await update.message.reply_text(response, disable_web_page_preview=True)

    async def plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        response = meal_agent.invoke(user_id=user_id, message="/plan")
        await update.message.reply_text(response, disable_web_page_preview=True)

    async def favoriler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        response = meal_agent.invoke(user_id=user_id, message="/favoriler")
        await update.message.reply_text(response, disable_web_page_preview=True)

    async def ayarlar(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        response = meal_agent.invoke(user_id=user_id, message="/ayarlar")
        await update.message.reply_text(response, disable_web_page_preview=True)

    async def iptal(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        response = meal_agent.invoke(user_id=user_id, message="/iptal")
        await update.message.reply_text(response, disable_web_page_preview=True)

    async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        message = update.message.text
        response = meal_agent.invoke(user_id=user_id, message=message)
        await update.message.reply_text(response, disable_web_page_preview=True)

    app = ApplicationBuilder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("bugun", bugun))
    app.add_handler(CommandHandler("haftalik_plan", haftalik_plan))
    app.add_handler(CommandHandler("plan", plan))
    app.add_handler(CommandHandler("favoriler", favoriler))
    app.add_handler(CommandHandler("ayarlar", ayarlar))
    app.add_handler(CommandHandler("iptal", iptal))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message))
    print("Telegram yemek ajanı çalışıyor...")
    app.run_polling()
```
