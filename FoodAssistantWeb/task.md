# Ana Ekran (Home Feed) Dönüşümü Görevleri

- `[x]` **Backend Geliştirmeleri**
  - `[x]` `app/main.py`: `GET /api/home-feed` endpoint'ini oluştur (Günün planı, haftanın planı ve favorileri çek).
  - `[x]` `app/llm.py`: `get_daily_suggestion` fonksiyonunu ekle. Prompt içerisine "favoriler arasından da seçilebilir" ve "haftanın diğer günlerine benzemesin" kısıtlamalarını ekle.

- `[x]` **Frontend HTML (`static/index.html`)**
  - `[x]` Top tabs yapısını `.bottom-nav` olarak alta taşı.
  - `[x]` Yeni `#home-panel` div'i oluştur (Arama çubuğu, Kapak Resmi, Öneriler).
  - `[x]` Mevcut sohbet kısmını arama çubuğuna entegre et veya gizle.

- `[x]` **Frontend CSS (`static/styles.css`)**
  - `[x]` `.bottom-nav` için sabit ve glassmorphism stillerini ekle.
  - `[x]` Kapak yemeği (Featured Card) için büyük görsel, blur efektli başlık, buton vs. stillerini ekle.
  - `[x]` Arama çubuğu (Top Search) stilini güncelle.

- `[x]` **Frontend JS (`static/app.js`)**
  - `[x]` Sayfa açılışında `GET /api/home-feed` çağrısı yapacak `loadHomeFeed()` fonksiyonu yaz.
  - `[x]` Gelen veriyi (Featured ve Alternatifler) DOM'a yerleştirecek render fonksiyonlarını yaz.
  - `[x]` Tab geçiş mantığını yeni `bottom-nav` yapısına uyarla.
