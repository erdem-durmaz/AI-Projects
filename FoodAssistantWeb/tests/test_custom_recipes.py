from app.db import (
    db_add_custom_recipe,
    db_delete_custom_recipe,
    db_find_custom_recipe_by_name,
    db_get_custom_recipe,
    db_list_custom_recipes,
    db_search_custom_recipes,
    db_update_custom_recipe,
)


def test_custom_recipe_crud():
    recipe = db_add_custom_recipe(
        "Mercimek Çorbası",
        ["1 su bardağı mercimek", "1 soğan"],
        ["Soğanı kavur", "Mercimeği ekle"],
        time="30 dk",
        servings="4 kişilik",
    )
    assert recipe["name"] == "Mercimek Çorbası"
    assert len(recipe["ingredients"]) == 2
    assert recipe["custom"] is True

    found = db_find_custom_recipe_by_name("mercimek corbasi")
    assert found is not None
    assert found["id"] == recipe["id"]

    updated = db_update_custom_recipe(
        recipe["id"],
        "Mercimek Çorbası",
        ["2 su bardağı mercimek"],
        ["Kaynat"],
    )
    assert updated["ingredients"] == ["2 su bardağı mercimek"]

    search = db_search_custom_recipes("mercimek")
    assert len(search) == 1

    assert len(db_list_custom_recipes()) == 1
    assert db_delete_custom_recipe(recipe["id"]) is True
    assert db_get_custom_recipe(recipe["id"]) is None


def test_custom_recipe_api(client):
    res = client.post(
        "/my-recipes/add",
        json={
            "name": "Fırında Tavuk",
            "ingredients": "2 tavuk but\n1 yk zeytinyağı",
            "steps": "Marine et\nFırınla",
            "time": "45 dk",
            "servings": "2 kişilik",
        },
    )
    assert res.status_code == 200
    recipe_id = res.json()["recipe"]["id"]

    res = client.get("/my-recipes")
    assert len(res.json()["recipes"]) == 1

    res = client.post("/recipe_by_name", json={"name": "Fırında Tavuk"})
    assert res.status_code == 200
    assert res.json()["result"]["custom"] is True
    assert res.json()["result"]["name"] == "Fırında Tavuk"

    res = client.post("/search", json={"query": "tavuk"})
    assert any(r.get("custom") for r in res.json()["results"])

    res = client.post("/recipe", json={"url": f"custom://{recipe_id}"})
    assert res.json()["result"]["type"] == "recipe"
