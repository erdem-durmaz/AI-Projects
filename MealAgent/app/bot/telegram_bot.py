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
        await update.message.reply_text(response)

    async def bugun(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        await update.message.reply_text("5 farklı kategoriden yemek önerisi arıyorum...")
        response = meal_agent.invoke(user_id=user_id, message="/bugun")
        await update.message.reply_text(response)

    async def haftalik_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        await update.message.reply_text("Haftalık planı gün gün oluşturmaya başlıyorum...")
        response = meal_agent.invoke(user_id=user_id, message="/haftalik_plan")
        await update.message.reply_text(response)

    async def plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        response = meal_agent.invoke(user_id=user_id, message="/plan")
        await update.message.reply_text(response)

    async def favoriler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        response = meal_agent.invoke(user_id=user_id, message="/favoriler")
        await update.message.reply_text(response)

    async def ayarlar(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        response = meal_agent.invoke(user_id=user_id, message="/ayarlar")
        await update.message.reply_text(response)

    async def iptal(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        response = meal_agent.invoke(user_id=user_id, message="/iptal")
        await update.message.reply_text(response)

    async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        message = update.message.text

        response = meal_agent.invoke(user_id=user_id, message=message)
        await update.message.reply_text(response)

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