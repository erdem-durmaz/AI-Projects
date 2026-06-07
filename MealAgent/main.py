from app.config import settings
from app.database import Database
from app.bot.telegram_bot import run_bot


def main():
    db = Database(settings.database_path)
    db.init_db()
    run_bot(db)


if __name__ == "__main__":
    main()