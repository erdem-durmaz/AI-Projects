from langchain_tavily import TavilySearch
from langchain_core.tools import tool
from database import get_connection
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent / ".env")

@tool
def search_recipes(query: str) -> str:
    """Verilen kritere göre internette yemek tarifi arar."""
    search = TavilySearch(max_results=5)
    raw = search.invoke(query + " tarifi")
    
    # Tavily dict olarak dönüyor
    if isinstance(raw, dict):
        results = raw.get("results", [])
    elif isinstance(raw, list):
        results = raw
    else:
        return str(raw)
    
    output = []
    for r in results:
        if isinstance(r, dict):
            title = r.get("title", "Başlık yok")
            url = r.get("url", "")
            content = r.get("content", "")[:200]
            output.append(f"🍽️ {title}\n🔗 {url}\n📝 {content}...\n")
    
    return "\n---\n".join(output) if output else "Sonuç bulunamadı."

@tool
def add_favorite(name: str, category: str = "", source_url: str = "", notes: str = "") -> str:
    """Beğenilen yemeği veritabanına ekler. category: fit, tatlı, pratik, kahvaltı, çorba"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO favorites (name, category, source_url, notes) VALUES (?, ?, ?, ?)",
        (name, category, source_url, notes)
    )
    conn.commit()
    conn.close()
    return f"✅ '{name}' favorilere eklendi."

@tool
def list_favorites(category: str = "") -> str:
    """Kaydedilmiş favori yemekleri listeler. category filtresi opsiyonel."""
    conn = get_connection()
    cursor = conn.cursor()
    if category:
        cursor.execute(
            "SELECT name, category, source_url, notes FROM favorites WHERE category LIKE ?",
            (f"%{category}%",)
        )
    else:
        cursor.execute("SELECT name, category, source_url, notes FROM favorites ORDER BY added_at DESC")
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return "Henüz favori yemek eklenmemiş."
    result = "📋 Favori Yemekler:\n\n"
    for name, cat, url, notes in rows:
        result += f"• {name}"
        if cat: result += f" [{cat}]"
        if url: result += f"\n  🔗 {url}"
        if notes: result += f"\n  📝 {notes}"
        result += "\n"
    return result

@tool
def create_weekly_plan(preferences: str = "") -> str:
    """Favori yemeklerden ve web aramasından haftalık yemek planı oluşturur."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, category, source_url FROM favorites")
    favorites = cursor.fetchall()

    days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    meals = ["Öğle", "Akşam"]

    today = datetime.now()
    week_start = today - timedelta(days=today.weekday())
    week_start_str = week_start.strftime("%Y-%m-%d")

    cursor.execute("DELETE FROM weekly_plan WHERE week_start = ?", (week_start_str,))

    total_slots = len(days) * len(meals)
    extra_meals = []

    if len(favorites) < total_slots:
        skip_words = [
            "tarif", "Tarif", "yemekleri", "Yemekleri", "http", "www", "#", "@",
            "YouTube", "youtube", "Pratik", "pratik", "Kolay", "kolay",
            "Cuisine", "cuisine", "Delicious", "dakika", "Dakika",
            "Yeni Ev", "playlist", "video", "izle", "Resimli", "resimli"
        ]

        queries = [
            f"{preferences} sebze yemeği tarifi" if preferences else "sebze yemeği tarifi",
            f"{preferences} et yemeği tarifi" if preferences else "tavuklu yemek tarifi",
            "çorba tarifi",
            "zeytinyağlı yemek tarifi",
        ]

        search = TavilySearch(max_results=5)
        for query in queries:
            if len(extra_meals) >= total_slots:
                break
            raw = search.invoke(query)
            results = raw.get("results", []) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
            for r in results:
                if isinstance(r, dict):
                    content = r.get("content", "")
                    url = r.get("url", "")
                    if "·" in content:
                        items = [x.strip() for x in content.split("·") if x.strip()]
                        for item in items:
                            if len(item) < 5 or len(item) > 50:
                                continue
                            if any(sw in item for sw in skip_words):
                                continue
                            # Duplicate kontrolü
                            if item not in [m[0] for m in extra_meals]:
                                extra_meals.append((item, "web", url))
        
        # Filtrelenecek kelimeler
        skip_words = [
    "tarif", "Tarif", "yemekleri", "Yemekleri", "http", "www", "#", "@",
    "YouTube", "youtube", "Pratik", "pratik", "Kolay", "kolay",
    "Cuisine", "cuisine", "Delicious", "dakika", "Dakika",
    "Yeni Ev", "playlist", "video", "izle", "Resimli", "resimli",
    "Besleyici", "Lezzetli", "çeşit", "Çeşit", "TARİFLERİ", "TARIF",
    "Videolu", "videolu", "21 ", "30 ", "18 ", "10 "
]

        for r in results:
            if isinstance(r, dict):
                content = r.get("content", "")
                url = r.get("url", "")
                if "·" in content:
                    items = [x.strip() for x in content.split("·") if x.strip()]
                    for item in items:
                        item = item.strip()
                        # Uzunluk filtresi: çok kısa veya çok uzun olmasın
                        if len(item) < 5 or len(item) > 50:
                            continue
                        # Skip kelimelerinden herhangi biri varsa atla
                        if any(sw in item for sw in skip_words):
                            continue
                        extra_meals.append((item, "web", url))

    all_meals = list(favorites) + extra_meals
    plan_text = f"📅 Haftalık Yemek Planı ({week_start.strftime('%d.%m.%Y')} haftası)\n\n"

    meal_index = 0
    for day in days:
        plan_text += f"{day}:\n"
        for meal_type in meals:
            if all_meals:
                meal_name, cat, url = all_meals[meal_index % len(all_meals)]
                meal_index += 1
            else:
                meal_name, url = "Belirlenmedi", ""
            cursor.execute(
                "INSERT INTO weekly_plan (week_start, day, meal_type, meal_name, source_url) VALUES (?, ?, ?, ?, ?)",
                (week_start_str, day, meal_type, meal_name, url or "")
            )
            plan_text += f"  {meal_type}: {meal_name}\n"
        plan_text += "\n"

    conn.commit()
    conn.close()
    return plan_text

@tool
def get_weekly_plan() -> str:
    """Mevcut haftalık planı gösterir."""
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime.now()
    week_start = today - timedelta(days=today.weekday())
    week_start_str = week_start.strftime("%Y-%m-%d")
    cursor.execute(
        "SELECT day, meal_type, meal_name, source_url FROM weekly_plan WHERE week_start = ? ORDER BY id",
        (week_start_str,)
    )
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return "Bu hafta için henüz plan oluşturulmamış. 'Haftalık plan yap' diyebilirsin."
    plan_text = "📅 Bu Haftanın Planı:\n\n"
    current_day = ""
    for day, meal_type, meal_name, url in rows:
        if day != current_day:
            plan_text += f"{day}:\n"
            current_day = day
        plan_text += f"  {meal_type}: {meal_name}"
        if url: plan_text += f" 🔗 {url}"
        plan_text += "\n"
    return plan_text

@tool
def suggest_meals_for_plan(preferences: str = "") -> str:
    """Haftalık plan için yemek önerileri getirir ve numaralı liste gösterir."""
    import os
    skip_words = [
        "tarif", "Tarif", "yemekleri", "Yemekleri", "http", "www", "#", "@",
        "YouTube", "youtube", "Pratik", "pratik", "Kolay", "kolay",
        "Cuisine", "cuisine", "Delicious", "dakika", "Dakika",
        "Yeni Ev", "playlist", "video", "izle", "Resimli", "resimli",
        "Besleyici", "Lezzetli", "çeşit", "Çeşit", "TARİFLERİ", "TARIF",
        "Videolu", "videolu", "21 ", "30 ", "18 ", "10 "
    ]

    queries = [
        f"{preferences} sebze yemeği" if preferences else "sebze yemeği tarifi",
        f"{preferences} tavuklu yemek" if preferences else "tavuklu yemek tarifi",
        "çorba tarifi",
        "zeytinyağlı yemek tarifi",
        "pratik et yemeği tarifi",
    ]

    collected = []
    search = TavilySearch(max_results=5)

    for query in queries:
        if len(collected) >= 20:
            break
        raw = search.invoke(query)
        results = raw.get("results", []) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
        for r in results:
            if isinstance(r, dict):
                content = r.get("content", "")
                url = r.get("url", "")
                if "·" in content:
                    for item in content.split("·"):
                        item = item.strip()
                        if len(item) < 5 or len(item) > 50:
                            continue
                        if any(sw in item for sw in skip_words):
                            continue
                        if item not in [m[0] for m in collected]:
                            collected.append((item, url))

    if not collected:
        return "Öneri bulunamadı, lütfen tekrar dene."

    # Geçici tabloyu temizle ve yeni önerileri kaydet
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM meal_suggestions")  # önceki önerileri sil
    for meal_name, url in collected:
        cursor.execute(
            "INSERT INTO meal_suggestions (user_id, meal_name, source_url) VALUES (?, ?, ?)",
            (0, meal_name, url)
        )
    conn.commit()
    conn.close()

    # Kullanıcıya numaralı liste göster
    result = "🍽️ Haftalık planın için yemek önerileri:\n\n"
    for i, (meal_name, url) in enumerate(collected, 1):
        result += f"{i}. {meal_name}\n"
    result += f"\nHangi yemekleri istiyorsun? Numara yaz: örn. '1,3,5,7,9,11,13'\n"
    result += f"(Haftanın 7 günü için en az 7, öğle+akşam için 14 seç)"

    return result


@tool
def save_selected_meals(selection: str) -> str:
    """Kullanıcının seçtiği numara listesini haftalık plana kaydeder. Örnek selection: '1,3,5,7'"""
    # Seçilen numaraları parse et
    try:
        selected_nums = [int(x.strip()) for x in selection.split(",") if x.strip().isdigit()]
    except:
        return "❌ Geçersiz format. Lütfen '1,3,5' şeklinde numara gir."

    if not selected_nums:
        return "❌ Hiç numara seçilmedi."

    # Önerilen yemekleri DB'den çek
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, meal_name, source_url FROM meal_suggestions ORDER BY id")
    suggestions = cursor.fetchall()

    selected_meals = []
    for num in selected_nums:
        if 1 <= num <= len(suggestions):
            _, meal_name, url = suggestions[num - 1]
            selected_meals.append((meal_name, url))

    if not selected_meals:
        conn.close()
        return "❌ Geçerli numara bulunamadı."

    # Haftalık planı oluştur
    days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    meal_types = ["Öğle", "Akşam"]

    today = datetime.now()
    week_start = today - timedelta(days=today.weekday())
    week_start_str = week_start.strftime("%Y-%m-%d")

    cursor.execute("DELETE FROM weekly_plan WHERE week_start = ?", (week_start_str,))

    plan_text = f"📅 Haftalık Yemek Planı ({week_start.strftime('%d.%m.%Y')} haftası)\n\n"
    meal_index = 0

    for day in days:
        plan_text += f"{day}:\n"
        for meal_type in meal_types:
            meal_name, url = selected_meals[meal_index % len(selected_meals)]
            meal_index += 1
            cursor.execute(
                "INSERT INTO weekly_plan (week_start, day, meal_type, meal_name, source_url) VALUES (?, ?, ?, ?, ?)",
                (week_start_str, day, meal_type, meal_name, url or "")
            )
            plan_text += f"  {meal_type}: {meal_name}\n"
        plan_text += "\n"

    conn.commit()
    conn.close()

    return plan_text + "✅ Plan kaydedildi! 'Planı göster' diyerek tekrar bakabilirsin."