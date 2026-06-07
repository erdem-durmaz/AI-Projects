# Yemek Asistanı

AI destekli Türk yemek planlama uygulaması. Groq LLM ile yemek önerisi, haftalık plan, favoriler ve Türk yemek sitelerinden tarif keşfi.

## Özellikler

- **Öner** — 8 kategoride yemek önerileri (tavuk, kırmızı et, balık, bakliyat, sebze, fit tarifler, fit tatlılar, zararlı ama lezzetli)
- **Haftalık plan** — Sürükle-bırak ile günlük yemek atama
- **Favoriler** — Sıralanabilir favori listesi
- **Tarif görüntüleme** — Öneri kartlarından 📖 ile kendi tariflerin veya yemek sitelerinden tarif
- **Kendi tariflerim** — Bulduğun tarifleri isim + malzeme + yapılış olarak kaydet
- **Tercihler** — Kişi sayısı, öğün, diyet tercihleri
- **Karanlık mod** ve **PWA** desteği

## Kurulum

```bash
pip install -r requirements.txt
cp .env.example .env
# .env dosyasına API anahtarlarını yaz
python app.py
```

Tarayıcıda: http://localhost:8000

## API Anahtarları

| Anahtar | Gerekli | Açıklama |
|---------|---------|----------|
| `GROQ_API_KEY` | Sohbet için | [console.groq.com](https://console.groq.com) |
| `TAVILY_API_KEY` | Keşfet için | [tavily.com](https://tavily.com) |

## Proje Yapısı

```
app/
  main.py      # FastAPI routes
  config.py    # Ayarlar
  db.py        # SQLite
  llm.py       # Groq entegrasyonu
  search.py    # Tavily + tarif fetch
  models.py    # Pydantic modeller
static/
  index.html
  app.js
  styles.css
  manifest.json
  sw.js
tests/
```

## Geliştirme

```bash
# Testler
pytest

# Lint
ruff check app tests
```

## Deploy

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Production için `.env` dosyasını sunucuda ayarlayın ve HTTPS kullanın.
