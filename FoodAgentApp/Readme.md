# 🍽️ Food Agent — Kişisel Yemek Asistanı

LangGraph + Groq + Telegram ile çalışan, yemek öneren, favorileri kaydeden ve haftalık plan yapan bir AI ajan.

---

## 📁 Dosya Yapısı

```
FoodAgentApp/
├── .env                # API key'ler (git'e ekleme!)
├── main.py             # Telegram bot loop, giriş noktası
├── agent.py            # LangGraph graph tanımı, LLM bağlantısı
├── tools.py            # Tüm tool fonksiyonları
├── database.py         # SQLite bağlantısı ve tablo oluşturma
├── food_agent.db       # SQLite veritabanı (otomatik oluşur)
└── README.md           # Bu dosya
```

---

## ⚙️ Kurulum

### 1. Gerekli paketler

```bash
pip install langgraph langchain langchain-groq langchain-tavily python-telegram-bot python-dotenv
```

### 2. `.env` dosyası

```
GROQ_API_KEY=...        # console.groq.com
TELEGRAM_BOT_TOKEN=...  # BotFather'dan
TAVILY_API_KEY=...      # app.tavily.com
```

### 3. Çalıştır

```bash
python main.py
```

---

## 🤖 Nasıl Çalışır

```
Telegram mesajı
      ↓
  LangGraph Agent (Groq / llama-3.1-8b-instant)
      ↓
  ┌─────────────────────────────────────────┐
  │  Hangi tool gerekli?                    │
  └──────┬──────────┬──────────┬────────────┘
         ↓          ↓          ↓
   search_      add/list_   suggest/save_
   recipes      favorites   meals + plan
         ↓          ↓          ↓
         └──────────────────────┘
                    ↓
             Telegram'a yanıt
```

### Graph akışı

```
[agent_node] → tool call var mı?
    ├── Evet → [tool_node] → [agent_node]  (sonucu yorumla)
    └── Hayır → END
```

---

## 🛠️ Tool'lar

| Tool | Ne yapar |
|------|----------|
| `search_recipes` | Tavily ile web'de tarif arar |
| `add_favorite` | Yemeği SQLite'a kaydeder |
| `list_favorites` | Kayıtlı favorileri listeler |
| `suggest_meals_for_plan` | Web'den yemek önerir, numaralı liste gösterir |
| `save_selected_meals` | Seçilen numaraları haftalık plana kaydeder |
| `get_weekly_plan` | Mevcut haftanın planını gösterir |
| `create_weekly_plan` | Otomatik plan oluşturur (seçimsiz) |

---

## 🗄️ Veritabanı

### `favorites`
| Kolon | Açıklama |
|-------|----------|
| `name` | Yemek adı |
| `category` | fit, tatlı, pratik, çorba... |
| `source_url` | Tarif linki |
| `notes` | Kullanıcı notu |

### `weekly_plan`
| Kolon | Açıklama |
|-------|----------|
| `week_start` | Pazartesi tarihi (YYYY-MM-DD) |
| `day` | Pazartesi ... Pazar |
| `meal_type` | Öğle / Akşam |
| `meal_name` | Yemek adı |

### `meal_suggestions`
Geçici tablo — `suggest_meals_for_plan` sonrası dolar, kullanıcı seçim yapınca `weekly_plan`'a taşınır.

---

## 💬 Telegram Kullanım Örnekleri

| Mesaj | Ne olur |
|-------|---------|
| `fit akşam yemeği öner` | Web'de arar, 5 öneri getirir |
| `tavuk sote favorilere ekle` | SQLite'a yazar |
| `favorilerimi göster` | Listeler |
| `haftalık plan öner` | 15-20 yemek önerir, numara seçtirtr |
| `1,3,5,7,9,11,13` | Seçilen yemekleri plana kaydeder |
| `planı göster` | Bu haftanın planını getirir |

---

## ⚠️ Bilinen Limitler

- **Groq ücretsiz plan:** 100k token/gün. Aşılırsa birkaç dakika bekle.
- **Model:** `llama-3.1-8b-instant` — hızlı ve token-verimli.
- **Session:** Bot yeniden başlatılırsa mesaj geçmişi sıfırlanır (SQLite verileri korunur).
- **Aynı anda tek instance:** Aynı bot token'ı ile iki `main.py` çalıştırma, Telegram Conflict hatası verir.

---

## 🔮 Sonraki Adımlar (Backlog)

- [ ] Her Pazartesi sabahı otomatik plan bildirimi
- [ ] Kahvaltı slotu ekleme
- [ ] Kalori / makro takibi
- [ ] Favorileri kategoriye göre filtreleme
- [ ] Instagram/TikTok içerik entegrasyonu