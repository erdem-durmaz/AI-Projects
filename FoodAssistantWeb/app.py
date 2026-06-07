"""
Yemek Asistanı — başlatıcı
Kurulum: pip install -r requirements.txt
Çalıştır: python app.py
"""

import uvicorn

if __name__ == "__main__":
    print("✅ http://localhost:8000 adresinde çalışıyor")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
