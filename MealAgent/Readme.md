# Meal Agent - LangGraph Yemek Planlama Asistanı

Bu proje, Telegram üzerinden çalışan ve LangGraph ile yönetilen bir **akşam yemeği planlama ajanı**dır. Ajan; kullanıcının belirlediği kriterlere göre web üzerinden yemek/tarif arar, Groq ile sonuçları filtreler, SQLite üzerinde hafıza tutar ve günlük/haftalık yemek seçimlerini kaydeder.

---

## 1. Projenin Amacı

Amaç, her gün “Bugün ne yesek?” sorusuna pratik ve kişiselleştirilmiş cevap verebilen bir yemek planlama asistanı oluşturmaktır.

Ajanın temel hedefleri:

- Her gün farklı kategorilerden yemek önerileri sunmak
- Haftalık akşam yemeği planını gün gün interaktif şekilde oluşturmak
- Beğenilen yemekleri favorilere kaydetmek
- Kullanıcının tercihlerini ve geçmiş seçimlerini SQLite üzerinde saklamak
- Tarif linklerini web üzerinden bulmak
- Cevapları kısa, sade ve sadece yemek adı + link formatında vermek

---

## 2. V1 Kapsamı

İlk versiyonda aşağıdaki özellikler yer alır:

- Telegram bot entegrasyonu
- LangGraph tabanlı workflow
- Groq ile LLM işlemleri
- Tavily ile web/tarif arama
- SQLite hafıza
- Günlük yemek önerisi
- Haftalık plan oluşturma
- Favorilere ekleme ve listeleme
- Kullanıcı tercihlerini gösterme
- Aktif akışı iptal etme

İlk versiyonda özellikle sade ve test edilebilir bir yapı hedeflenmiştir.

---

## 3. İlk Versiyonda Olmayan Özellikler

Aşağıdaki özellikler bilinçli olarak V1 dışında bırakılmıştır:

- Evdeki malzemelere göre öneri
- Instagram / TikTok scraping
- YouTube tarif analizi
- Kalori hesabı
- Alışveriş listesi
- Web arayüzü
- Otomatik günlük bildirim
- Çok kullanıcılı gelişmiş yetkilendirme
- Favorilere göre öneri ağırlıklandırma

Bu özellikler sonraki fazlarda modüler şekilde eklenebilir.

---

## 4. Kullanıcı Tercihleri

Ajan şu varsayılan tercihlere göre öneri üretir:

- Kişi sayısı: 3
- Öğün: Sadece akşam yemeği
- Yemek tarzı: Ev yemeği
- Öncelikler:
  - Hafif
  - Fit
  - Pratik
  - Düşük kalorili
  - Proteinli
  - Glutensiz
  - Sebze ağırlıklı
  - Tavuk ağırlıklı
  - Dana eti ağırlıklı
  - Fırın yemeği
  - Tencere yemeği

Kesinlikle önerilmeyecekler:

- Kuzu eti
- Uzakdoğu mutfağı
- Noodle
- Soya sosu
- Teriyaki
- Sushi
- Ramen
- Wok tarzı yemekler

---

## 5. Öneri Mantığı

Ajan her öneri setinde **3 değil, 5 farklı kategoriden** yemek önerir.

Kategoriler:

1. Tavuk ağırlıklı
2. Dana/et ağırlıklı, kuzu hariç
3. Sebze ağırlıklı
4. Bakliyat / proteinli ev yemeği
5. Fit ve glutensiz hafif alternatif

Örnek çıktı:

```text
Bugün için 5 farklı kategoriden seçenek:

1) [Tavuk] Fırında Sebzeli Tavuk
https://...

2) [Dana/Et] Etli Türlü
https://...

3) [Sebze] Zeytinyağlı Kabak Yemeği
https://...

4) [Bakliyat] Nohutlu Sebze Yemeği
https://...

5) [Fit Glutensiz] Yoğurtlu Karnabahar Salatası
https://...

Seçmek için 1, 2, 3, 4 veya 5 yazabilirsin.
```

---

## 6. Haftalık Planlama Akışı

Haftalık planlama **Yöntem A** ile çalışır: gün gün interaktif seçim.

Akış:

1. Kullanıcı `/haftalik_plan` komutunu gönderir.
2. Bot Pazartesi için 5 seçenek sunar.
3. Kullanıcı 1-5 arasında seçim yapar.
4. Bot seçimi kaydeder ve Salı gününe geçer.
5. Aynı akış Pazar gününe kadar devam eder.
6. Tüm hafta tamamlandığında haftalık plan gösterilir.

Örnek:

```text
/haftalik_plan
```

Bot:

```text
Pazartesi için 5 farklı kategoriden seçenek:

1) [Tavuk] ...
2) [Dana/Et] ...
3) [Sebze] ...
4) [Bakliyat] ...
5) [Fit Glutensiz] ...

Pazartesi için hangisini seçelim?
```

Kullanıcı:

```text
2
```

Bot seçimi kaydeder ve Salı için yeni seçenekler üretir.

---

## 7. Telegram Komutları

### `/start`

Botu başlatır ve kullanılabilir komutları gösterir.

### `/bugun`

Bugün için 5 farklı kategoriden yemek önerisi üretir.

### `/haftalik_plan`

Haftalık akşam yemeği planını gün gün oluşturmaya başlar.

### `/plan`

Mevcut haftalık planı gösterir.

### `/favoriler`

Favori yemekleri listeler.

### `/ayarlar`

Varsayılan yemek tercihlerini gösterir.

### `/iptal`

Aktif haftalık plan veya seçim akışını iptal eder.

---

## 8. Serbest Mesaj Örnekleri

Ajan komut dışındaki bazı mesajları da anlayacak şekilde tasarlanmıştır.

Örnekler:

```text
favorilerimi göster
```

```text
bunu favorilere ekle
```

```text
haftalık planı göster
```

```text
bugün yemek konuşmayalım
```

```text
1
```

`1`, `2`, `3`, `4`, `5` seçimleri aktif akışa göre yorumlanır:

- Aktif haftalık plan varsa: haftalık plan seçimi
- Aktif haftalık plan yoksa: günlük yemek seçimi

---

## 9. Teknik Mimari

Genel akış:

```text
Telegram Bot
    ↓
Message Router
    ↓
LangGraph Workflow
    ↓
Tools
    ├── Recipe Search Tool
    ├── Favorites Tool
    ├── Daily Choice Tool
    ├── Weekly Plan Tool
    └── Preferences Tool
    ↓
SQLite Database
```

LLM tarafı:

```text
Groq
 ├── Web arama sonuçlarını filtreler
 ├── 5 farklı kategoriden yemek seçer
 ├── Yasaklı içerikleri eler
 └── JSON formatında sonuç döner
```

Web arama tarafı:

```text
Tavily Search API
 ├── Tarif sitelerinden sonuç getirir
 ├── Her kategori için ayrı arama yapar
 └── Sonuçları Groq'a filtreleme için verir
```

---

## 10. Proje Klasör Yapısı

```text
meal-agent/
│
├── .env
├── .env.example
├── requirements.txt
├── main.py
│
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── state.py
│   ├── prompts.py
│   ├── llm.py
│   └── graph.py
│
├── app/tools/
│   ├── __init__.py
│   ├── recipe_search.py
│   ├── favorites.py
│   ├── weekly_plan.py
│   ├── daily_choice.py
│   └── preferences.py
│
├── app/bot/
│   ├── __init__.py
│   └── telegram_bot.py
│
└── data/
    └── meals.db
```

---

## 11. Dosyaların Görevleri

### `main.py`

Uygulamayı başlatır. Veritabanını initialize eder ve Telegram botu çalıştırır.

### `app/config.py`

`.env` dosyasındaki ayarları okur.

### `app/database.py`

SQLite bağlantısını ve tüm veritabanı işlemlerini yönetir.

### `app/state.py`

LangGraph state yapısını tanımlar.

### `app/prompts.py`

Groq için kullanılan sistem promptlarını ve yemek kriterlerini içerir.

### `app/llm.py`

Groq client wrapper dosyasıdır. Chat ve JSON cevap alma işlemlerini yönetir.

### `app/graph.py`

LangGraph workflow'unu kurar. Router ve action node burada yer alır.

### `app/tools/recipe_search.py`

Tavily ile web araması yapar ve Groq ile 5 kategori önerisini seçtirir.

### `app/tools/favorites.py`

Favorilere ekleme ve favorileri listeleme işlemlerini yapar.

### `app/tools/daily_choice.py`

Günlük yemek seçimini kaydeder.

### `app/tools/weekly_plan.py`

Haftalık plan akışını yönetir.

### `app/tools/preferences.py`

Kullanıcı tercihlerini gösterir.

### `app/bot/telegram_bot.py`

Telegram bot komutlarını ve mesaj handlerlarını içerir.

---

## 12. SQLite Tabloları

### `user_preferences`

Kullanıcının varsayılan tercihlerini saklar.

Alanlar:

- `user_id`
- `people_count`
- `meal_type`
- `criteria`
- `exclusions`
- `created_at`
- `updated_at`

### `favorites`

Favori yemekleri saklar.

Alanlar:

- `id`
- `user_id`
- `title`
- `url`
- `category`
- `created_at`

### `daily_choices`

Günlük seçilen yemekleri saklar.

Alanlar:

- `id`
- `user_id`
- `choice_date`
- `title`
- `url`
- `category`
- `created_at`

### `weekly_plan`

Haftalık planı saklar.

Alanlar:

- `id`
- `user_id`
- `week_start`
- `day_name`
- `title`
- `url`
- `category`
- `created_at`

### `recipe_candidates`

Botun sunduğu geçici seçenekleri saklar.

Bu tablo önemli çünkü kullanıcı sadece `1`, `2`, `3`, `4` veya `5` yazdığında, bot bu seçimin hangi yemeğe karşılık geldiğini buradan bulur.

Alanlar:

- `id`
- `user_id`
- `flow_type`
- `day_name`
- `option_no`
- `title`
- `url`
- `category`
- `source`
- `created_at`

### `active_flow`

Devam eden haftalık plan akışını saklar.

Alanlar:

- `user_id`
- `flow_type`
- `current_day_index`
- `week_start`
- `created_at`
- `updated_at`

### `last_selected`

Son seçilen yemeği saklar. “Bunu favorilere ekle” komutu bu tabloyu kullanır.

Alanlar:

- `user_id`
- `title`
- `url`
- `category`
- `updated_at`

---

## 13. Kurulum

### 1. Proje klasörünü oluştur

```bash
mkdir meal-agent
cd meal-agent
```

### 2. Sanal ortam oluştur

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Mac/Linux:

```bash
source .venv/bin/activate
```

### 3. Paketleri kur

```bash
pip install -r requirements.txt
```

### 4. `.env` dosyasını oluştur

Mac/Linux:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
copy .env.example .env
```

### 5. `.env` içine API bilgilerini gir

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
GROQ_API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key

GROQ_MODEL=llama-3.3-70b-versatile
DATABASE_PATH=data/meals.db
TIMEZONE=Europe/Istanbul
```

### 6. Uygulamayı çalıştır

```bash
python main.py
```

Başarılı çalışırsa terminalde şu mesaj görünür:

```text
Telegram yemek ajanı çalışıyor...
```

---

## 14. Test Senaryoları

### Senaryo 1: Botu başlatma

Telegram'da:

```text
/start
```

Beklenen sonuç:

- Bot komut listesini gösterir.

---

### Senaryo 2: Günlük öneri alma

```text
/bugun
```

Beklenen sonuç:

- Bot 5 farklı kategoriden yemek önerisi döner.

---

### Senaryo 3: Günlük seçim yapma

```text
2
```

Beklenen sonuç:

- Bot 2 numaralı yemeği bugünkü yemek olarak kaydeder.

---

### Senaryo 4: Favoriye ekleme

```text
bunu favorilere ekle
```

Beklenen sonuç:

- Son seçilen yemek favorilere eklenir.

---

### Senaryo 5: Favorileri listeleme

```text
/favoriler
```

Beklenen sonuç:

- Favori yemekler listelenir.

---

### Senaryo 6: Haftalık plan oluşturma

```text
/haftalik_plan
```

Beklenen sonuç:

- Bot Pazartesi için 5 seçenek sunar.
- Kullanıcı seçim yaptıkça Salı, Çarşamba, Perşembe, Cuma, Cumartesi ve Pazar günlerine ilerler.
- Hafta tamamlanınca plan gösterilir.

---

### Senaryo 7: Planı gösterme

```text
/plan
```

Beklenen sonuç:

- Mevcut haftalık plan gösterilir.

---

### Senaryo 8: Akışı iptal etme

```text
/iptal
```

Beklenen sonuç:

- Aktif haftalık plan akışı iptal edilir.

---

## 15. Geliştirme Notları

Bu V1 özellikle sade tutulmuştur. İlk hedef, botun uçtan uca çalışmasıdır.

Öncelikli debug noktaları:

1. Tavily sonuçları bazen tarif dışı sayfa döndürebilir.
2. Groq bazen JSON formatını bozabilir.
3. Aynı yemek farklı isimlerle tekrar gelebilir.
4. Bazı tariflerde gizli olarak kuzu eti veya Uzakdoğu malzemeleri geçebilir.
5. Linkler bazen doğrudan tarif sayfası olmayabilir.

Bunlar için sonraki versiyonlarda şu iyileştirmeler yapılabilir:

- JSON retry mekanizması
- URL/title validasyonu
- Domain filtreleme
- Sadece Türkçe tarif sitelerine öncelik verme
- Son 7 gün yenilen yemekleri daha güçlü dışlama
- “Beğenmedim, başka 5 seçenek getir” komutu
- Favorilere göre öneri ağırlıklandırma
- Haftalık planda kategori dengesini daha sıkı kontrol etme

---

## 16. V2 İçin Önerilen Özellikler

V2 için önerilen geliştirmeler:

- Otomatik günlük Telegram bildirimi
- Haftalık plan için alışveriş listesi
- Web arayüzü
- Kullanıcı tercihlerini Telegram üzerinden güncelleme
- “Bunu bir daha önerme” komutu
- Favorilerden otomatik plan oluşturma
- Tarif detayını isteğe bağlı gösterme
- Kalori/protein tahmini
- Google Sheets veya Notion entegrasyonu
- Çok kullanıcı desteği

---

## 17. Özet

Bu proje, günlük yemek kararını kolaylaştırmak için tasarlanmış modüler bir LangGraph ajanıdır.

V1’in ana mantığı:

```text
Kullanıcı Telegram'dan komut verir
→ LangGraph mesajı router'dan geçirir
→ Gerekli tool çalışır
→ Tavily web sonuçlarını getirir
→ Groq sonuçları filtreler
→ SQLite hafıza güncellenir
→ Bot kısa ve linkli cevap döner
```

İlk hedef, stabil çalışan bir Telegram prototipidir. Proje modüler kurulduğu için sonraki fazlarda web arayüzü, alışveriş listesi, otomatik bildirim ve gelişmiş tercih yönetimi kolayca eklenebilir.


meal-agent/
│
├── .env
├── .env.example
├── requirements.txt
├── main.py
│
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── state.py
│   ├── prompts.py
│   ├── llm.py
│   └── graph.py
│
├── app/tools/
│   ├── __init__.py
│   ├── recipe_search.py
│   ├── favorites.py
│   ├── weekly_plan.py
│   ├── daily_choice.py
│   └── preferences.py
│
├── app/bot/
│   ├── __init__.py
│   └── telegram_bot.py
│
└── data/
    └── meals.db