import os
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from langchain_core.messages import HumanMessage

from database import init_db
from agent import food_agent

load_dotenv()

# Her kullanıcı için ayrı mesaj geçmişi (session)
user_sessions: dict[int, list] = {}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    
    print(f"[{user_id}] → {user_text}")
    
    # Kullanıcının geçmiş mesajlarını al (yoksa başlat)
    if user_id not in user_sessions:
        user_sessions[user_id] = []
    
    # Yeni mesajı geçmişe ekle
    user_sessions[user_id].append(HumanMessage(content=user_text))
    
    # Typing göstergesi
    await update.message.chat.send_action("typing")
    
    try:
        # Agent'ı çalıştır
        result = await asyncio.to_thread(
            food_agent.invoke,
            {"messages": user_sessions[user_id]}
        )
        
        # Agent'ın son yanıtını al
        last_message = result["messages"][-1]
        response_text = last_message.content
        
        # Groq bazen tool call'ı text olarak ekliyor, temizle
        if isinstance(response_text, list):
            response_text = " ".join([b.get("text", "") for b in response_text if isinstance(b, dict)])
        
        # <function=...> kalıplarını temizle
        import re
        response_text = re.sub(r'<function=\w+>.*?</function>', '', response_text, flags=re.DOTALL).strip()
        response_text = re.sub(r'<function=\w+\{.*?\}', '', response_text, flags=re.DOTALL).strip()
        
        # Yanıtı geçmişe ekle
        user_sessions[user_id] = result["messages"]
        
        # Geçmişi max 20 mesajda tut (token tasarrufu)
        if len(user_sessions[user_id]) > 20:
            user_sessions[user_id] = user_sessions[user_id][-20:]
        
        await update.message.reply_text(response_text)
        print(f"[{user_id}] ← {response_text[:100]}...")
        
    except Exception as e:
        error_msg = f"Bir hata oluştu: {str(e)}"
        print(f"HATA: {e}")
        await update.message.reply_text(error_msg)


def main():
    # DB'yi başlat
    init_db()
    
    # Telegram bot
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()
    
    # Tüm metin mesajlarını dinle
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 Food Agent başladı. Telegram'dan mesaj gönder!")
    app.run_polling()


if __name__ == "__main__":
    main()