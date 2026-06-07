# Ana Ekranı "Keşfet" (Home Feed) Akışına Dönüştürme Planı

Şu anki sistemde uygulama doğrudan "Yapay Zekayla Sohbet" (Ne yiyelim?) ekranıyla açılıyor. Kullanıcının talebi doğrultusunda, uygulamayı attığımız premium mockup fotoğrafındaki gibi şık bir **Keşfet (Home Feed)** akışına dönüştüreceğiz.

## ⚠️ User Review Required

Lütfen aşağıdaki değişikliklere göz atıp onay verin veya değiştirmek istediğiniz yerleri belirtin.

### 1. Navigasyon Değişikliği (Alt Bar)
- Üstte bulunan `[Öner | Plan | Tariflerim | Ayarlar]` sekmelerini kaldıracağız.
- Bunun yerine, tıpkı mockup'taki gibi ekranın **altına** sabitlenmiş şık bir `[Keşfet | Plan | Tariflerim | Profil]` menüsü (Bottom Navigation Bar) ekleyeceğiz.

### 2. Yeni "Keşfet" (Ana Ekran) Tasarımı
- Uygulama açıldığında direkt sohbet kutusu yerine **"Bugünün Önerileri"** ekranı açılacak.
- **Eğer o gün için Haftalık Plan'a yemek eklediyseniz:** O yemek devasa bir kapak fotoğrafıyla (Featured Card) en üstte çıkacak. Altında "Tarife Git" butonu olacak.
- **Eğer planınız boşsa:** Yapay zeka sizin profil tercihlerinizi (sevdiğiniz/sevmediğiniz şeyler) baz alarak o güne özel, sürpriz bir "Günün Yemeği" belirleyecek ve onu büyük kartta sunacak.
- Büyük kartın altında, tıpkı mockup'taki gibi yana/aşağı kaydırılabilen alternatif yemek kartları (Mercimek Çorbası vs.) listelenecek.

### 3. Arama Çubuğu
- Mockup'taki gibi en üste geniş ve şık bir "Tarif ara..." çubuğu yerleştireceğiz. Yapay zekaya sormak istediğiniz soruları (Sohbet) bu arama çubuğunu kullanarak yapmaya devam edebileceksiniz.

## Proposed Changes

---

### UI / CSS Değişiklikleri (`static/index.html` & `static/styles.css`)

#### [MODIFY] index.html
- `<div class="tabs">` yapısı `<nav class="bottom-nav">` olarak ekranın altına taşınacak.
- Yeni bir `<div id="home-panel">` eklenecek ve varsayılan açılış ekranı olacak.
- Sohbet kutusu (`.input-area`), `home-panel` içindeki şık bir üst arama çubuğuna (Top Search Bar) dönüştürülecek.

#### [MODIFY] styles.css
- `bottom-nav` için sabit (fixed) konumlandırma ve bulanık cam (glass) efektleri yazılacak.
- Mockup'taki "Featured Card" (Kapaklı büyük yemek kartı) için özel CSS class'ları eklenecek. Büyük resim, zorluk derecesi, süre, ve parlak renkli buton stilleri eklenecek.

---

### Backend / LLM Değişiklikleri (`app/main.py` & `app/llm.py`)

#### [MODIFY] main.py
- Yeni bir `GET /home-feed` API ucu (endpoint) açılacak. Bu endpoint:
  1. Hangi günde olduğumuzu bulacak (Örn: Çarşamba).
  2. Veritabanından (Plan tablosu) Çarşamba'nın yemeklerini çekecek.
  3. Yemek varsa onu getirecek. Yoksa `llm.py` üzerinden günün yemeği için yapay zekaya istek atacak.

#### [MODIFY] llm.py
- `get_daily_suggestion(prefs)` adında yeni bir fonksiyon yazılacak. Bu fonksiyon yapay zekadan kısa ve öz olarak sadece 1 adet ana yemek, 2 adet de yan yemek önermesini ve bunların tahmini süresini/zorluk derecesini dönmesini isteyecek.

## Verification Plan

### Manual Verification
1. Uygulamayı canlıda açıp açılış ekranının Koyu Cam (Dark Glass) temalı büyük bir "Bugünün Önerisi" kartıyla açıldığını test etmek.
2. Plana (Örn: Salı) bir yemek ekleyip, uygulamaya Salı günü girildiğinde ana ekranda yapay zeka önerisi yerine plandaki yemeğin kapak fotoğrafıyla çıktığını görmek.
3. Alt menü çubuğunun (Bottom Nav) sayfalar arası geçişi bozmadan çalışmasını teyit etmek.
