import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.resolve()))

from app.llm import get_daily_suggestion
from app.db import db_get_preferences, db_get_plan, db_get_favorites

prefs = db_get_preferences()
plan = db_get_plan()
favs = db_get_favorites()

try:
    print("Fetching daily suggestion...")
    suggestion = get_daily_suggestion(prefs, plan, favs)
    print("SUCCESS:")
    print(suggestion)
except Exception as e:
    print(f"ERROR: {e}")
