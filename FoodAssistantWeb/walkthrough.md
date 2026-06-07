# Keşfet (Home Feed) Ekranı Güncellemesi Tamamlandı! 🎉

Geri bildiriminiz doğrultusunda, uygulamamızı çok daha premium hissettiren **"Keşfet"** mimarisine taşıdım. Artık doğrudan bir sohbet botu ekranı açılmak yerine, kullanıcıyı görsel olarak şölen yaşatan zengin bir arayüz karşılıyor.

## Neler Değişti?

### 1. Şık Alt Menü (Bottom Navigation)
Üstteki sekmeler yerine, günümüz modern mobil uygulamalarındaki gibi ekranın en altında sabit duran buzlu cam tasarımlı bir menü çubuğu (Bottom Nav) eklendi.
- **🧭 Keşfet:** Yeni ana sayfanız.
- **💬 Asistan:** Eski sohbet yapay zekası buraya taşındı.
- **📅 Plan:** Sadece haftalık seçimlerin olduğu plan sekmesi.
- **⭐ Defterim:** Favorileriniz ve Şefin Spesyalleri.
- **📒 Tarifler:** Kendi tarifleriniz.

### 2. Akıllı "Bugünün Önerisi" (Featured Card)
Uygulamaya girer girmez sizi devasa bir yemek görseliyle "Bugünün Önerisi" karşılıyor. Bu öneri rastgele değil, çok zekice bir mantıkla çalışıyor:
1. **Planda Varsa:** Eğer o gün (Örn: Çarşamba) için zaten plana bir yemek eklemişseniz, ana ekranda direkt **"Sizin Planınız"** olarak o yemek çıkıyor.
2. **Planda Yoksa:** Yapay zeka devreye giriyor!
   - O hafta boyunca planınıza eklediğiniz **diğer yemeklere bakıyor** (örneğin pazartesi tavuk, salı balık yediğinizi anlıyor).
   - Profil ayarlarınızı ve **favoriye eklediğiniz yemekleri** tarıyor.
   - Bunların hepsini harmanlayarak, o gün için "sıkıcı olmayan" ve haftanın geri kalanıyla çakışmayan mükemmel bir **Kapak Yemeği (Featured Meal)** seçiyor!

### 3. Alternatifler
Kapak yemeğinin hemen altında, eğer onu beğenmezseniz diye yapay zekanın sunduğu 2-3 adet alternatif yemek kartı yatay bir liste şeklinde sunuluyor.

### 4. Hızlı Arama
Ana ekranın en üstündeki "Tarif veya yemek ara..." çubuğundan doğrudan arama yapabilirsiniz. Bir şey yazdığınız an otomatik olarak "Sohbet" sekmesine geçer ve Asistan sizin yerinize bu menüyü veya tarifi bulur.

---

### 5. Akıllı Çevrimdışı ve Hata Modu (Offline Fallback)
Yapay zeka servisi (Groq API vb.) limit aşımı (429) veya bağlantı hatası verdiğinde sayfa yükleniyorda kalmaz:
- Veritabanınızda (Neon.tech) favori veya şefin spesyali yemekleriniz varsa, sistem bunları otomatik olarak karıştırarak günün önerisi ve alternatifleri olarak sunar (Çevrimdışı Mod).
- Eğer listeniz boşsa, sistem önceden tanımlanmış lezzetli bir klasik Türk yemek menüsü önerir.
- İnternet veya sunucu tamamen koptuğunda ise arayüzde şık bir "Tekrar Dene" kartı gösterilir.

### 6. 👨‍🍳 Şefin Spesyali (Chef's Specials) Entegrasyonu
- **Veritabanı Katmanı:** Neon.tech PostgreSQL veritabanında `chef_specials` tablosu oluşturuldu. Bir yemek hem favori hem de şefin spesyali olabilecek bağımsız bir yapıya kavuşturuldu.
- **Yapay Zeka & Fallback:** LLM promptu güncellendi; yapay zeka günün önerisinde şefin spesyallerine öncelik tanıyacaktır. Çevrimdışı/Limit aşımı fallback modunda da bu yemekler en üstte öne çıkan öneri olarak sunulur.
- **Arayüz (UI/UX):** 
  - Plan sekmesinde favorilerin altına drag-and-drop / SortableJS destekli şık bir **👨‍🍳 Şefin Spesyalleri** alanı eklendi.
  - Yemek kartlarına favori butonunun (⭐) yanına şefin spesyali butonu (👨‍🍳 / aktifken 👑) eklendi.

### 7. 🎨 Dikey Kart Boyutu Genişletmesi
- Ana ekrandaki kapak yemeği kartı görselinin `.featured-img` yüksekliği `240px`'ten `360px`'e çıkarıldı. Görselin daha fazla kısmı görünür hale getirilerek modern, ferah ve premium bir görünüm sağlandı.

---

### 8. 📅 Plan ve Defterim Sekmesi Ayrımı & Ayarlar Çekmecesi (Drawer)
- **Plan Temizliği:** "Plan" tabından Favoriler ve Şefin Spesyalleri listeleri tamamen kaldırıldı; bu sekmede sadece haftalık seçimlerinize yer verildi.
- **Defterim Tabı:** Favoriler ve Şefin Spesyalleri "Defterim" (⭐) adlı yepyeni bir sekmeye taşındı.
- **Ayarlar Drawer'ı:** Arayüzün 5 tab sınırını korumak için Ayarlar sekmesi, sağ üstteki ⚙️ butonuna basıldığında açılan, sağdan kayarak gelen şık bir çekmece paneline (Drawer Overlay) dönüştürüldü. Tercihler kaydedildiğinde bu panel otomatik olarak kapanır.

---

> [!TIP]
> **Nasıl Test Edilir?**
> 1. Tarayıcıyı yenileyin. Sağ üstteki ⚙️ butonuna basarak Ayarlar çekmecesinin sağdan akıcı bir şekilde açıldığını görün.
> 2. Ayarları doldurup "Kaydet" dediğinizde çekmecenin kapandığını ve tercihlerin kaydedildiğini doğrulayın.
> 3. Alt menüden "Plan" sekmesine tıklayın; burada sadece haftalık grid düzeninin olduğunu gözlemleyin.
> 4. "Defterim" sekmesine geçiş yaparak Favoriler ve Şefin Spesyalleri listelerinizin, sürükle-bırak alanlarının buraya taşındığını ve sorunsuz çalıştığını görün.


