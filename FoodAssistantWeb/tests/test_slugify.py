from app.search import slugify


def test_slugify_turkish():
    assert slugify("Mercimek Çorbası") == "mercimek-corbasi"
    assert slugify("Tavuk Şiş") == "tavuk-sis"


def test_slugify_special_chars():
    assert slugify("Kısır (Salata)") == "kisir-salata"
