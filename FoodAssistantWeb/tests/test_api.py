def test_root(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "Yemek Asistanı" in res.text


def test_favorites_flow(client):
    res = client.post("/favorites/add", json={"name": "Mantı"})
    assert res.status_code == 200
    assert "Mantı" in res.json()["favorites"]

    res = client.get("/favorites")
    assert "Mantı" in res.json()["favorites"]

    res = client.post("/favorites/remove", json={"name": "Mantı"})
    assert "Mantı" not in res.json()["favorites"]


def test_plan_invalid_day(client):
    res = client.post("/plan/add", json={"day": "InvalidDay", "meal": "Test"})
    assert res.status_code == 422


def test_plan_multiple_meals(client):
    res = client.post("/plan/add", json={"day": "Cuma", "meal": "İmambayıldı"})
    assert res.status_code == 200
    assert res.json()["plan"]["Cuma"] == ["İmambayıldı"]

    res = client.post("/plan/add", json={"day": "Cuma", "meal": "Cacık"})
    assert res.json()["plan"]["Cuma"] == ["İmambayıldı", "Cacık"]

    res = client.post("/plan/remove", json={"day": "Cuma", "meal": "İmambayıldı"})
    assert res.json()["plan"]["Cuma"] == ["Cacık"]


def test_preferences(client):
    res = client.post(
        "/preferences",
        json={
            "person_count": "2",
            "meal_type": "Kahvaltı",
            "style": "Hafif",
            "preferences": "Yumurta",
            "dislikes": "Sucuk",
        },
    )
    assert res.status_code == 200
    assert res.json()["preferences"]["person_count"] == "2"


def test_chat_without_api_key(client, monkeypatch):
    monkeypatch.setattr("app.main.GROQ_API_KEY", "")
    res = client.post("/chat", json={"message": "Ne yiyelim?", "history": []})
    assert res.status_code == 503
