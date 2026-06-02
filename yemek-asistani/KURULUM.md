# 🍽️ Yemek Asistanı — Kurulum Kılavuzu

## Sistem Mimarisi

```
Telegram Grubu
    ↕
n8n (localhost:5678)   ←→   Ollama (llama3.2:3b)
    ↕
Docker (local makine)
```

---

## 1. Ön Gereksinimler

- **Docker Desktop** kurulu olmalı (Windows/Mac) veya **Docker Engine** (Linux)
- **Telegram Bot Token** (BotFather'dan alınmış)
- **Telegram Grup Chat ID** (aşağıda açıklanıyor)

---

## 2. Telegram Grubu ve Bot Kurulumu

### 2a. Telegram Grubu Oluştur
1. Telegram'da yeni bir grup oluştur (örn: "Akşam Yemekleri")
2. İki kişiyi gruba ekle
3. Botunu gruba **admin** olarak ekle

### 2b. Chat ID'yi Bul
Botunu gruba ekledikten sonra tarayıcıdan şu adresi aç:
```
https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
```
Çıkan JSON'da `"chat":{"id": -XXXXXXXXX}` kısmındaki sayıyı al.
> ⚠️ Grup ID'leri genellikle **negatif** sayıdır (örn: `-1001234567890`)

---

## 3. Kurulum

### Seçenek A: Otomatik Kurulum (Linux/Mac)
```bash
cd yemek-asistani
chmod +x kur.sh
./kur.sh
```

### Seçenek B: Manuel Kurulum

**Adım 1:** `.env` dosyası oluştur:
```
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHI...
TELEGRAM_CHAT_ID=-1001234567890
```

**Adım 2:** Docker Compose başlat:
```bash
docker compose up -d
```

**Adım 3:** Model indirilmesini bekle (~2-5 dakika, internet hızına göre):
```bash
docker logs ollama-init -f
```
`Model indirildi!` mesajını görünce devam et.

---

## 4. n8n Ayarları

### 4a. n8n'e Giriş
- Tarayıcıda: http://localhost:5678
- Kullanıcı: `admin`
- Şifre: `admin123`

### 4b. Telegram Credential Ekle
1. Sol menü → **Credentials** → **Add Credential**
2. **Telegram API** seç
3. Bot Token'ını gir
4. İsim: `Telegram Bot`
5. **Save** tıkla

### 4c. Workflow'u İçe Aktar
1. Sol menü → **Workflows** → **Import from file**
2. `workflows/yemek-asistani.json` dosyasını seç
3. **Import** tıkla

### 4d. Environment Variables Tanımla
n8n'de Variables (Değişkenler) oluşturman gerekiyor:

1. Sol menü → **Settings** → **Variables**
2. Şu değişkenleri ekle:

| İsim | Başlangıç Değeri |
|------|-----------------|
| `TELEGRAM_CHAT_ID` | Grup Chat ID'n (örn: -1001234567890) |
| `YEMEK_KURALLARI` | `Sağlıklı ve ev yapımı yemekler tercih et. Kızartmadan kaçın. Sebze ağırlıklı ol.` |
| `GECMIS_ONERILER` | *(boş bırak)* |

### 4e. Workflow'u Aktif Et
1. Workflow'u aç
2. Sağ üstteki **Inactive** düğmesine tıkla → **Active** yap
3. ✅ Sistem çalışmaya hazır!

---

## 5. Kullanım

### Otomatik Mesaj
Her gün **15:00**'de (İstanbul saati) gruba şu mesaj gelir:

```
🍽️ Akşam Yemeği Asistanı

Bugün akşam yemeği için öneri hazırlamamı ister misin?

Cevapla:
1️⃣ - Evdeki malzemelere göre öner
2️⃣ - Bana direkt öneri ver
3️⃣ - Hafif bir şey öner
```

### Yanıt Akışı

**1 yazarsan:**
→ Bot "Evde hangi malzemeler var?" diye sorar
→ Malzemeleri yazarsın (örn: `tavuk, patates, soğan`)
→ Bot o malzemelere göre tarif önerir

**2 yazarsan:**
→ Bot direkt bir Türk yemeği önerir

**3 yazarsan:**
→ Bot hafif, az kalorili bir şey önerir

### Manuel Tetikleme
Gruba `/yemek` yazarak istediğin zaman öneri isteyebilirsin.

---

## 6. Yemek Kurallarını Telegram'dan Güncelle

Gruba şu formatta mesaj gönder:
```
/ayarla Sağlıklı ve ev yapımı yemekler. Gluten içermemeli. Az tuzlu olsun.
```

Bot onaylayacak:
```
✅ Yemek kuralları güncellendi!
Yeni kurallar: Sağlıklı ve ev yapımı yemekler...
```

---

## 7. Sistemin Durdurulması / Yeniden Başlatılması

```bash
# Durdur
docker compose down

# Yeniden başlat
docker compose up -d

# Logları gör
docker compose logs -f n8n
docker compose logs -f ollama
```

---

## 8. Sorun Giderme

### Bot mesaj almıyor
- Botun gruba admin olarak eklendiğinden emin ol
- Chat ID'nin doğru olduğunu kontrol et (negatif sayı mı?)
- n8n'de Telegram webhook'unun aktif olduğunu kontrol et

### Ollama yanıt vermiyor
```bash
# Modelin yüklendiğini kontrol et
docker exec ollama ollama list

# Modeli manuel indir
docker exec ollama ollama pull llama3.2:3b
```

### n8n açılmıyor
```bash
docker compose restart n8n
```

---

## 9. Örnek Kural Metinleri

Telegram'dan `/ayarla` komutuyla güncelleyebilirsin:

**Sağlıklı Odaklı:**
```
/ayarla Sağlıklı Türk mutfağı yemekleri öner. Kızartma yok, az yağlı pişirme yöntemleri tercih et. Sebze ve baklagil ağırlıklı olsun.
```

**Hızlı Yemekler:**
```
/ayarla 30 dakika altında hazırlanabilecek kolay Türk yemekleri öner. Pratik tarifler tercih et.
```

**Mevsimsel:**
```
/ayarla Mevsim sebzelerini kullanan, güncel malzemelerle yapılabilecek yemekler öner.
```
