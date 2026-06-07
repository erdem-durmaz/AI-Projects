from app.db import (
    db_add_favorite,
    db_add_plan_meal,
    db_get_favorites,
    db_get_plan,
    db_get_preferences,
    db_remove_favorite,
    db_remove_plan_meal,
    db_set_preferences,
    db_add_chef_special,
    db_get_chef_specials,
    db_remove_chef_special,
)


def test_favorites_crud():
    db_add_favorite("Mercimek Çorbası")
    db_add_favorite("Tavuk Sote")
    assert db_get_favorites() == ["Mercimek Çorbası", "Tavuk Sote"]
    db_remove_favorite("Mercimek Çorbası")
    assert db_get_favorites() == ["Tavuk Sote"]


def test_chef_specials_crud():
    db_add_chef_special("İskender")
    db_add_chef_special("Mantı")
    assert db_get_chef_specials() == ["İskender", "Mantı"]
    db_remove_chef_special("İskender")
    assert db_get_chef_specials() == ["Mantı"]


def test_plan_multiple_meals():
    db_add_plan_meal("Pazartesi", "Karnıyarık")
    db_add_plan_meal("Pazartesi", "Mercimek Çorbası")
    plan = db_get_plan()
    assert plan["Pazartesi"] == ["Karnıyarık", "Mercimek Çorbası"]
    db_remove_plan_meal("Pazartesi", "Karnıyarık")
    assert db_get_plan()["Pazartesi"] == ["Mercimek Çorbası"]


def test_preferences():
    db_set_preferences({"person_count": "4", "meal_type": "Öğle yemeği"})
    prefs = db_get_preferences()
    assert prefs["person_count"] == "4"
    assert prefs["meal_type"] == "Öğle yemeği"

