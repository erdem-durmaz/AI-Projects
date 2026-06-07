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