import json
import logging
import re

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from app.config import CATEGORY_ORDER, GROQ_API_KEY, MAX_HISTORY_MESSAGES, MODEL_NAME

logger = logging.getLogger(__name__)

MEAL_JSON_SCHEMA = """1. Genel yemek önerisi (örn: "ne yiyelim", "akşama fikir ver"):
{
  "type": "meal_suggestion",
  "categories": {
    "tavuk":            ["Yemek 1", "Yemek 2", "Yemek 3", "Yemek 4", "Yemek 5"],
    "kirmizi_et":       ["Yemek 1", "Yemek 2", "Yemek 3", "Yemek 4", "Yemek 5"],
    "balik":            ["Yemek 1", "Yemek 2", "Yemek 3", "Yemek 4", "Yemek 5"],
    "bakliyat":         ["Yemek 1", "Yemek 2", "Yemek 3", "Yemek 4", "Yemek 5"],
    "sebze":            ["Yemek 1", "Yemek 2", "Yemek 3", "Yemek 4", "Yemek 5"],
    "fit_tarifler":     ["Yemek 1", "Yemek 2", "Yemek 3", "Yemek 4", "Yemek 5"],
    "fit_tatlilar":     ["Yemek 1", "Yemek 2", "Yemek 3", "Yemek 4", "Yemek 5"],
    "zararli_lezzetli": ["Yemek 1", "Yemek 2", "Yemek 3", "Yemek 4", "Yemek 5"]
  }
}

2. Spesifik bir yemek/tarif isteniyorsa (örn: "pilav öner", "tavuklu pilav tarifi ver"):
{
  "type": "recipe_search",
  "query": "istenen yemek adı veya malzeme (ör: tavuklu pilav)"
}"""


def build_system_prompt(prefs: dict[str, str]) -> str:
    return f"""Sen bir Türk yemek asistanısın. Görevin kullanıcının niyetini anlayıp SADECE uygun JSON'ı döndürmek.

KULLANICI TERCİHLERİ:
- Kişi sayısı: {prefs.get('person_count', '3')}
- Öğün: {prefs.get('meal_type', 'Akşam yemeği')}
- Tarz: {prefs.get('style', 'Ev yemeği')}
- Tercihler: {prefs.get('preferences', '')}

KESİNLİKLE ÖNERİLMEYECEKLER:
- {prefs.get('dislikes', '')}

KATEGORİLER (Sadece meal_suggestion için):
- tavuk: Tavuk yemekleri
- kirmizi_et: Kırmızı et yemekleri (dana, kıyma vb.)
- balik: Balık ve deniz ürünleri
- bakliyat: Bakliyat, pilav, makarna, börek
- sebze: Sebze ağırlıklı yemekler, zeytinyağlılar, salatalar
- fit_tarifler: Düşük kalorili, sağlıklı ana yemekler
- fit_tatlilar: Fit/sağlıklı tatlılar
- zararli_lezzetli: Hamburger, pizza, kızartmalar, tatlılar — lezzetli ama "günah" yemekler :)

KURALLAR:
1. HER mesajda SADECE aşağıdaki 2 JSON formatından birini döndür. Asla düz metin, açıklama veya tarif yazma.
2. "ne yiyelim", "akşama fikir ver" gibi genel isteklerde 'meal_suggestion' döndür. Her kategoride FARKLI 5 yemek olsun.
3. "pilav öner", "tavuklu pilav nasıl yapılır" gibi spesifik yemek sorularında 'recipe_search' döndür.
4. Yemekle ilgisiz mesajlarda bile en mantıklı olanı (genelde meal_suggestion) üret, genel sohbet yapma.

{MEAL_JSON_SCHEMA}
"""


def trim_history(history: list, max_messages: int = MAX_HISTORY_MESSAGES) -> list:
    if len(history) <= max_messages:
        return history
    return history[-max_messages:]


def history_to_messages(history: list) -> list:
    messages = []
    for msg in history:
        role = msg.get("role")
        content = msg.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    return messages


def _extract_meal_json(raw: str) -> dict | None:
    clean = re.sub(r"```json|```", "", raw).strip()
    candidates = [clean]
    match = re.search(r'\{[\s\S]*"type"\s*:\s*"(?:meal_suggestion|recipe_search)"[\s\S]*\}', raw)
    if match:
        candidates.append(match.group())
    for text in candidates:
        try:
            parsed = json.loads(text)
            if parsed.get("type") == "meal_suggestion" and parsed.get("categories"):
                return {"type": "meal", "data": parsed["categories"]}
            elif parsed.get("type") == "recipe_search" and parsed.get("query"):
                return {"type": "search", "query": parsed["query"]}
        except (json.JSONDecodeError, TypeError):
            continue
    return None


def normalize_meal_categories(categories: dict) -> dict:
    normalized = {}
    for key in CATEGORY_ORDER:
        items = categories.get(key, [])
        if isinstance(items, list):
            cleaned = [str(i).strip() for i in items if str(i).strip()][:5]
            if cleaned:
                normalized[key] = cleaned
    return normalized


def parse_meal_response(raw: str) -> tuple[str, dict | None]:
    extracted = _extract_meal_json(raw)
    if extracted:
        if extracted["type"] == "meal":
            meal_data = normalize_meal_categories(extracted["data"])
            if meal_data:
                return "__MEAL__", meal_data
        elif extracted["type"] == "search":
            return "__SEARCH__", {"query": extracted["query"]}
    return raw, None


def get_llm(temperature: float = 1.0, max_tokens: int = 2000) -> ChatGroq:
    return ChatGroq(
        api_key=GROQ_API_KEY,
        model=MODEL_NAME,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def _invoke_meal(message: str, history: list, prefs: dict[str, str]) -> str:
    llm = get_llm()
    trimmed = trim_history(history)
    messages = [SystemMessage(content=build_system_prompt(prefs))] + history_to_messages(trimmed)
    messages.append(HumanMessage(content=message))
    return llm.invoke(messages).content.strip()


def chat_completion(message: str, history: list, prefs: dict[str, str]) -> tuple[str, dict | None]:
    raw = _invoke_meal(message, history, prefs)
    code, parsed_data = parse_meal_response(raw)
    if parsed_data:
        return code, parsed_data

    logger.warning("LLM returned non-JSON, retrying: %s", raw[:120])
    retry_msg = (
        f"{message}\n\n"
        "[ZORUNLU: Sadece meal_suggestion VEYA recipe_search JSON döndür. Düz metin veya açıklama YAZMA.]"
    )
    raw = _invoke_meal(retry_msg, history, prefs)
    return parse_meal_response(raw)


def chat_stream(message: str, history: list, prefs: dict[str, str]):
    llm = get_llm()
    trimmed = trim_history(history)
    messages = [SystemMessage(content=build_system_prompt(prefs))] + history_to_messages(trimmed)
    messages.append(HumanMessage(content=message))
    for chunk in llm.stream(messages):
        if chunk.content:
            yield chunk.content


def random_meal_name() -> str:
    llm = get_llm(temperature=1.0, max_tokens=60)
    resp = llm.invoke(
        [HumanMessage(content="Rastgele bir Türk akşam yemeği adı söyle, sadece ismi yaz.")]
    )
    return resp.content.strip().split("\n")[0]


def parse_page_content(clean_text: str) -> dict:
    llm = get_llm(temperature=0.1, max_tokens=1200)
    prompt = f"""Aşağıdaki metin bir yemek sitesinden alınmıştır.

Önce sayfanın ne olduğuna karar ver:
- Eğer birden fazla yemek adı/listesi içeriyorsa → "list"
- Eğer tek bir yemeğin tarifi ise → "recipe"

"list" ise SADECE şu JSON formatında döndür:
{{
  "type": "list",
  "items": ["Yemek adı 1", "Yemek adı 2", "Yemek adı 3"]
}}

"recipe" ise SADECE şu JSON formatında döndür:
{{
  "type": "recipe",
  "name": "Yemeğin tam adı",
  "ingredients": ["miktar + malzeme 1", "miktar + malzeme 2"],
  "steps": ["adım 1", "adım 2"],
  "time": "süre (varsa)",
  "servings": "kaç kişilik (varsa)"
}}

Başka hiçbir şey yazma, sadece JSON döndür.

İçerik:
{clean_text[:4000]}"""
    result = llm.invoke([HumanMessage(content=prompt)]).content.strip()
    parsed = re.sub(r"```json|```", "", result).strip()
    return json.loads(parsed)
