#!/bin/bash
# ==============================================
# Yemek Asistanı - Kurulum Scripti
# ==============================================

set -e

echo ""
echo "🍽️  Yemek Asistanı Kurulum Scripti"
echo "======================================"
echo ""

# .env dosyası oluştur
if [ ! -f ".env" ]; then
  echo "📝 .env dosyası oluşturuluyor..."
  
  read -p "Telegram Bot Token'ınızı girin: " BOT_TOKEN
  read -p "Telegram Grup Chat ID'nizi girin: " CHAT_ID
  
  cat > .env << EOF
TELEGRAM_BOT_TOKEN=${BOT_TOKEN}
TELEGRAM_CHAT_ID=${CHAT_ID}
EOF
  
  echo "✅ .env dosyası oluşturuldu."
else
  echo "ℹ️  .env dosyası zaten mevcut, atlanıyor."
fi

echo ""
echo "🐳 Docker Compose başlatılıyor..."
docker compose up -d

echo ""
echo "⏳ Servisler başlatılıyor (30 saniye bekleniyor)..."
sleep 30

echo ""
echo "🤖 Ollama model indirme durumu kontrol ediliyor..."
docker logs ollama-init --tail 20

echo ""
echo "======================================"
echo "✅ Kurulum tamamlandı!"
echo ""
echo "📌 Sonraki adımlar:"
echo "   1. http://localhost:5678 adresine git"
echo "   2. Kullanıcı: admin  |  Şifre: admin123"
echo "   3. KURULUM.md dosyasındaki adımları takip et"
echo "======================================"
