"""
LangGraph: Food Supervisor Multi-Agent System
=============================================
Mimari:
                    ┌─────────────┐
                    │  SUPERVISOR │  ← hangi agent'ı çağıracağına KENDISI karar verir
                    └──────┬──────┘
       ┌──────────┬─────────┴──────────┬──────────┐
       ▼          ▼                    ▼          ▼
 ┌──────────┐ ┌──────────┐      ┌──────────┐ ┌──────────┐
 │  recipe  │ │  search  │      │ favorite │ │  chat    │
 │  agent   │ │  agent   │      │  agent   │ │  agent   │
 └──────────┘ └──────────┘      └──────────┘ └──────────┘
    Tarif        Araştırma         Favori       Genel
   internetten   (fit tarifler     kaydetme     sohbet
   arar          vb.) bulur        işlemi

Araçlar:
- Groq API    : LLM (hızlı ve ücretsiz)
- Tavily      : web arama (ücretsiz 1000/ay, kayıt: tavily.com)
- DuckDuckGo  : yedek arama seçeneği (API key yok)

Kurulum:
    pip install langgraph langchain-groq langchain-community
    pip install tavily-python duckduckgo-search python-dotenv

.env dosyan:
    GROQ_API_KEY=gsk_...
    TAVILY_API_KEY=tvly-...   ← isteğe bağlı, yoksa DuckDuckGo kullanılır
"""

# ─────────────────────────────────────────────
# 1. IMPORT'LAR
# ─────────────────────────────────────────────

import os
import json
from typing import Annotated, Sequence, TypedDict, List, Optional

from dotenv import load_dotenv

from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
    ToolMessage
)
from langchain_core.tools import tool
from langchain_groq import ChatGroq                          # Groq LLM
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

load_dotenv()


# ─────────────────────────────────────────────
# 2. WEB ARAMA ARAÇLARI SETUP
# ─────────────────────────────────────────────
# Tavily varsa Tavily, yoksa DuckDuckGo kullan

def get_search_tool():
    """
    Tavily API key varsa Tavily, yoksa DuckDuckGo döndür.
    İkisi de aynı .invoke({"query": "..."}) interface'ini kullanır.
    """
    if os.getenv("TAVILY_API_KEY"):
        print("✅ Tavily arama motoru kullanılıyor")
        return TavilySearchResults(max_results=5)
    else:
        # DuckDuckGo — API key gerektirmez
        print("ℹ️  Tavily bulunamadı, DuckDuckGo kullanılıyor")
        try:
            from langchain_community.tools import DuckDuckGoSearchRun
            return DuckDuckGoSearchRun()
        except ImportError:
            raise ImportError("pip install duckduckgo-search komutu ile yükle")

# Global arama aracı — tüm agent'lar paylaşır
search_tool = get_search_tool()


# ─────────────────────────────────────────────
# 3. STATE TANIMI
# ─────────────────────────────────────────────
# myreAct.py'deki AgentState ile aynı temel.
# Ek: favorites listesi — favorite_agent buraya yazar, her agent okuyabilir.

class AgentState(TypedDict):
    # Konuşma geçmişi — add_messages ile birikir, üzerine yazılmaz
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # Supervisor'ın bir sonraki agent kararı
    next: str

    # Hangi agent'lar çalıştı (Supervisor takip için kullanır)
    completed_tasks: List[str]

    # Favori yemekler listesi — favorite_agent yönetir
    favorites: List[str]

    # Search agent'ın bulduğu son yemek listesi
    # favorite_agent bunları okur
    last_search_results: List[str]


# ─────────────────────────────────────────────
# 4. TOOL TANIMLARI
# ─────────────────────────────────────────────

# ── Recipe Agent Tool'u ───────────────────────
@tool
def search_recipe(dish_name: str) -> str:
    """
    Verilen yemek adı için internetten detaylı tarif arar.
    Malzemeler ve yapılış adımlarını döndürür.
    """
    print(f"   🔍 Tarif aranıyor: {dish_name}")
    query = f"{dish_name} tarifi malzemeler yapılış adımları"
    try:
        result = search_tool.invoke({"query": query})
        # Tavily liste döndürür, DuckDuckGo string döndürür — normalize et
        if isinstance(result, list):
            content = "\n\n".join([
                r.get("content", r.get("snippet", str(r)))
                for r in result[:3]
            ])
        else:
            content = str(result)
        return f"{dish_name} tarifi:\n{content}"
    except Exception as e:
        return f"Arama hatası: {str(e)}"


# ── Search Agent Tool'u ───────────────────────
@tool
def search_food_info(query: str) -> str:
    """
    Yemekle ilgili araştırma yapar: fit tarifler, kalori bilgisi,
    diyet alternatifleri, sağlıklı pişirme yöntemleri vb.
    """
    print(f"   🔍 Araştırılıyor: {query}")
    try:
        result = search_tool.invoke({"query": query})
        if isinstance(result, list):
            content = "\n\n".join([
                r.get("content", r.get("snippet", str(r)))
                for r in result[:5]
            ])
        else:
            content = str(result)
        return content
    except Exception as e:
        return f"Arama hatası: {str(e)}"


@tool
def extract_dish_names(text: str) -> str:
    """
    Bir metinden yemek isimlerini çıkarır ve liste olarak döndürür.
    Search agent'ın bulduğu sonuçlardan yemek adlarını ayıklamak için kullanılır.
    """
    # Bu tool LLM tarafından çağrılır, parametre olarak metin alır
    # Gerçek extraction LLM'in kendisi tarafından yapılır
    return f"Metinden çıkarılan yemekler: {text}"


# ── Favorite Agent Tool'ları ──────────────────
@tool
def add_to_favorites(dish_name: str) -> str:
    """
    Bir yemeği favoriler listesine ekler.
    dish_name: eklenecek yemeğin adı
    """
    # State'e doğrudan yazamayız, mesaj olarak döndürüyoruz
    # Graph node'u bu mesajı okuyup state'i güncelleyecek
    return f"FAVORITE_ADD:{dish_name}"


@tool
def remove_from_favorites(dish_name: str) -> str:
    """
    Bir yemeği favoriler listesinden çıkarır.
    dish_name: çıkarılacak yemeğin adı
    """
    return f"FAVORITE_REMOVE:{dish_name}"


@tool
def list_favorites() -> str:
    """Mevcut favori listesini gösterir."""
    return "FAVORITE_LIST"


# ── Chat Agent Tool'u ─────────────────────────
@tool
def search_general_info(query: str) -> str:
    """
    Yemek dışı konularda internette güncel bilgi arar.
    Haber, spor, teknoloji, seyahat vb. her türlü konu için kullanılır.
    """
    print(f"   🔍 Genel arama: {query}")
    try:
        result = search_tool.invoke({"query": query})
        if isinstance(result, list):
            content = "\n\n".join([
                r.get("content", r.get("snippet", str(r)))
                for r in result[:5]
            ])
        else:
            content = str(result)
        return content
    except Exception as e:
        return f"Arama hatası: {str(e)}"


# ─────────────────────────────────────────────
# 5. MODEL SETUP
# ─────────────────────────────────────────────
# Groq API — ChatOpenAI ile aynı interface, çok daha hızlı

# Supervisor için — tool'suz, sadece karar verir
supervisor_model = ChatGroq(
    model="llama-3.3-70b-versatile",  # en iyi ücretsiz Groq modeli
    temperature=0,                     # karar verirken tutarlılık önemli
    api_key=os.getenv("GROQ_API_KEY")
)

# Her agent için tool'larını bind et
# myreAct.py'deki model = ChatOllama(...).bind_tools(tools) ile aynı
recipe_model = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.3,
    api_key=os.getenv("GROQ_API_KEY")
).bind_tools([search_recipe])

search_model = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.3,
    api_key=os.getenv("GROQ_API_KEY")
).bind_tools([search_food_info, extract_dish_names])

favorite_model = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY")
).bind_tools([add_to_favorites, remove_from_favorites, list_favorites])

chat_model = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.7,   # genel sohbet için biraz daha yaratıcı
    api_key=os.getenv("GROQ_API_KEY")
).bind_tools([search_general_info])

# Tool dict'leri — myRAGAgent.py'deki tools_dict pattern'i
recipe_tools_dict   = {"search_recipe": search_recipe}
search_tools_dict   = {"search_food_info": search_food_info, "extract_dish_names": extract_dish_names}
favorite_tools_dict = {"add_to_favorites": add_to_favorites, "remove_from_favorites": remove_from_favorites, "list_favorites": list_favorites}
chat_tools_dict     = {"search_general_info": search_general_info}


# ─────────────────────────────────────────────
# 6. SUPERVISOR NODE
# ─────────────────────────────────────────────
# Tamamen özerk — biz sadece "elinde şu uzmanlar var" diyoruz.
# Kimi ne zaman çağıracağına MODEL kendisi karar veriyor.

def supervisor(state: AgentState) -> AgentState:
    print(f"\n{'='*50}")
    print(f"🎯 [SUPERVISOR] Değerlendiriliyor...")
    print(f"   Tamamlanan: {state.get('completed_tasks', [])}")
    print(f"   Favoriler:  {state.get('favorites', [])}")

    system_prompt = SystemMessage(content=f"""
Sen bir asistan ekibinin yöneticisisin.
Kullanıcının mesajını ve konuşma geçmişini değerlendirerek
hangi uzmanın çalışması gerektiğine karar ver.

UZMAN EKİBİN:
- recipe_agent   : Yemek tariflerini internetten arar ve getirir
- search_agent   : Yemekle ilgili araştırma yapar (fit tarifler, kalori, diyet vb.)
- favorite_agent : Yemekleri favorilere ekler, çıkarır veya listeler
- chat_agent     : Yemek dışı konularda güncel bilgi getirir

ŞİMDİYE KADAR ÇALIŞANLAR: {state.get('completed_tasks', []) or 'Henüz kimse çalışmadı'}
FAVORİLER: {state.get('favorites', []) or 'Boş'}
SON ARAMA SONUÇLARI: {state.get('last_search_results', []) or 'Yok'}

KARAR KURALLARI:
- Kullanıcı tarif istiyorsa → recipe_agent (daha önce çalışmadıysa)
- Kullanıcı araştırma, fit alternatif, sağlıklı seçenek istiyorsa → search_agent (daha önce çalışmadıysa)
- Kullanıcı favorilere ekle/çıkar/listele diyorsa → favorite_agent
- Kullanıcı yemek dışı bir konu soruyorsa → chat_agent
- Bir agent zaten çalıştıysa ve sonuç aldıysa → FINISH de, tekrar aynı agent'ı çağırma
- Tüm istekler karşılandıysa → FINISH

ÖNEMLİ: Aynı agent'ı arka arkaya 2 kez çağırma. Zaten çalışmışsa FINISH de.

SADECE şu seçeneklerden birini yaz, başka hiçbir şey yazma:
recipe_agent | search_agent | favorite_agent | chat_agent | FINISH
""")

    response = supervisor_model.invoke([system_prompt] + list(state["messages"]))
    decision = response.content.strip().lower().split()[0]  # ilk kelimeyi al

    valid = ["recipe_agent", "search_agent", "favorite_agent", "chat_agent", "finish"]
    if decision not in valid:
        for v in valid:
            if v in response.content.lower():
                decision = v
                break
        else:
            decision = "chat_agent"  # fallback

    if decision == "finish":
        decision = "FINISH"

    print(f"🎯 [SUPERVISOR] Karar → {decision}")

    return {
        "messages": [AIMessage(content=f"Yönlendirme: {decision}")],
        "next": decision,
        "completed_tasks": state.get("completed_tasks", []),
        "favorites": state.get("favorites", []),
        "last_search_results": state.get("last_search_results", [])
    }


# ─────────────────────────────────────────────
# 7. AGENT NODE'LARI
# ─────────────────────────────────────────────

def run_agent(state, agent_model, agent_tools_dict, agent_name, system_content) -> AgentState:
    """
    Tekrar kullanılabilir agent çalıştırıcı.
    myreAct.py'deki model_call + tool execute mantığını birleştiriyor.
    """
    print(f"\n🤖 [{agent_name.upper()}] Çalışıyor...")

    system_prompt = SystemMessage(content=system_content)
    response = agent_model.invoke([system_prompt] + list(state["messages"]))

    new_messages = [response]
    new_favorites = list(state.get("favorites", []))
    new_search_results = list(state.get("last_search_results", []))

    # Tool çağrısı var mı? — myreAct.py'deki should_continue mantığı
    if hasattr(response, "tool_calls") and response.tool_calls:
        print(f"   🔧 Tool'lar: {[tc['name'] for tc in response.tool_calls]}")

        for tc in response.tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]

            if tool_name not in agent_tools_dict:
                result = f"Bilinmeyen tool: {tool_name}"
            else:
                try:
                    result = agent_tools_dict[tool_name].invoke(tool_args)
                    print(f"   ✓ {tool_name}")

                    # Favorite tool'larının özel sonuçlarını işle
                    if isinstance(result, str):
                        if result.startswith("FAVORITE_ADD:"):
                            dish = result.replace("FAVORITE_ADD:", "").strip()
                            if dish not in new_favorites:
                                new_favorites.append(dish)
                                result = f"✅ '{dish}' favorilere eklendi. Güncel liste: {new_favorites}"
                            else:
                                result = f"ℹ️ '{dish}' zaten favorilerde."
                        elif result.startswith("FAVORITE_REMOVE:"):
                            dish = result.replace("FAVORITE_REMOVE:", "").strip()
                            if dish in new_favorites:
                                new_favorites.remove(dish)
                                result = f"✅ '{dish}' favorilerden çıkarıldı. Güncel liste: {new_favorites}"
                            else:
                                result = f"ℹ️ '{dish}' favorilerde bulunamadı."
                        elif result == "FAVORITE_LIST":
                            result = f"⭐ Favoriler: {new_favorites if new_favorites else 'Boş'}"

                except Exception as e:
                    result = f"Hata: {str(e)}"
                    print(f"   ✗ {tool_name} → {e}")

            # myreAct.py'deki ToolMessage pattern'i
            new_messages.append(ToolMessage(
                tool_call_id=tc["id"],
                name=tool_name,
                content=str(result)
            ))

            # Search sonuçlarını state'e kaydet — favorite_agent okuyacak
            if tool_name == "search_food_info" and isinstance(result, str):
                new_search_results = [result[:500]]  # özet olarak sakla

    return {
        "messages": new_messages,
        "next": "",
        "completed_tasks": state.get("completed_tasks", []) + [agent_name],
        "favorites": new_favorites,
        "last_search_results": new_search_results
    }


def recipe_agent(state: AgentState) -> AgentState:
    return run_agent(
        state, recipe_model, recipe_tools_dict, "recipe_agent",
        """Sen bir tarif uzmanısın.
Kullanıcının istediği yemeğin tarifini internetten ara ve getir.
Malzemeleri ve adımları net şekilde listele. Türkçe yanıt ver."""
    )


def search_agent(state: AgentState) -> AgentState:
    return run_agent(
        state, search_model, search_tools_dict, "search_agent",
        """Sen bir beslenme araştırmacısısın.
Kullanıcının istediği konuyu (fit tarifler, sağlıklı alternatifler, 
kalori bilgisi vb.) internette araştır ve sonuçları listele.
Bulduğun yemek isimlerini açıkça belirt. Türkçe yanıt ver."""
    )


def favorite_agent(state: AgentState) -> AgentState:
    return run_agent(
        state, favorite_model, favorite_tools_dict, "favorite_agent",
        f"""Sen favori listesi yöneticisisin.
Kullanıcının isteğine göre favorilere ekle, çıkar veya listele.
Mevcut favoriler: {state.get('favorites', [])}
Son arama sonuçları (seçim yapılabilir): {state.get('last_search_results', [])}
Türkçe yanıt ver."""
    )


def chat_agent(state: AgentState) -> AgentState:
    return run_agent(
        state, chat_model, chat_tools_dict, "chat_agent",
        """Sen genel bilgi asistanısın.
Yemek dışındaki konularda kullanıcının sorularını yanıtla.
Güncel bilgi gerekiyorsa internette ara. Türkçe yanıt ver."""
    )


# ─────────────────────────────────────────────
# 8. SHOULD CONTINUE — CONDITIONAL EDGE
# ─────────────────────────────────────────────
# myreAct.py'deki should_continue ile aynı pattern.

def should_continue(state: AgentState) -> str:
    next_step = state.get("next", "FINISH")
    print(f"   [ROUTER] → {next_step}")
    return next_step


# ─────────────────────────────────────────────
# 9. GRAPH KURULUMU
# ─────────────────────────────────────────────

graph = StateGraph(AgentState)

# Node'ları ekle
graph.add_node("supervisor",    supervisor)
graph.add_node("recipe_agent",   recipe_agent)
graph.add_node("search_agent",   search_agent)
graph.add_node("favorite_agent", favorite_agent)
graph.add_node("chat_agent",     chat_agent)

# Giriş noktası
graph.set_entry_point("supervisor")

# Supervisor'dan conditional edge
graph.add_conditional_edges(
    "supervisor",
    should_continue,
    {
        "recipe_agent":   "recipe_agent",
        "search_agent":   "search_agent",
        "favorite_agent": "favorite_agent",
        "chat_agent":     "chat_agent",
        "FINISH":         END
    }
)

# Her agent → supervisor'a geri dön
graph.add_edge("recipe_agent",   "supervisor")
graph.add_edge("search_agent",   "supervisor")
graph.add_edge("favorite_agent", "supervisor")
graph.add_edge("chat_agent",     "supervisor")

app = graph.compile()


# ─────────────────────────────────────────────
# 10. ÇALIŞTIRMA — İnteraktif Sohbet
# ─────────────────────────────────────────────
# memory_agent.py'deki conversation_history pattern'i —
# konuşma geçmişi birikir, bot bağlamı hatırlar.

def print_last_message(state: dict):
    """Son agent mesajını yazdır (supervisor kararlarını atla)."""
    if "messages" not in state:
        return
    messages = list(state["messages"])
    # Geriye doğru tara, ilk anlamlı AI veya Tool mesajını bul
    for msg in reversed(messages):
        if isinstance(msg, ToolMessage):
            print(f"\n🛠️  SONUÇ: {msg.content[:500]}")
            break
        elif isinstance(msg, AIMessage) and "Yönlendirme:" not in msg.content:
            print(f"\n🤖 ASİSTAN: {msg.content[:800]}")
            break


if __name__ == "__main__":

    print("\n🚀 ===== FOOD ASSISTANT =====")
    print("Çıkmak için 'exit' yaz\n")
    print("Örnek komutlar:")
    print("  • mercimek çorbası tarifi ver")
    print("  • fit tavuk tarifleri araştır")
    print("  • mercimek çorbasını favorilere ekle")
    print("  • favorilerimi göster")
    print("  • bugün hava nasıl İstanbul'da\n")

    # memory_agent.py'deki conversation_history pattern'i
    conversation_history = []
    favorites = []

    while True:
        user_input = input("\nSen: ").strip()

        if user_input.lower() in ["exit", "çıkış", "quit"]:
            print(f"\n👋 Görüşürüz! Favorilerin: {favorites}")
            break

        if not user_input:
            continue

        conversation_history.append(HumanMessage(content=user_input))

        # State'i her turda güncelle — memory_agent.py ile aynı pattern
        inputs = {
            "messages": conversation_history,
            "next": "",
            "completed_tasks": [],
            "favorites": favorites,
            "last_search_results": []
        }

        try:
            # stream ile çalıştır — son state'i de yakala
            final_state = None
            for step in app.stream(inputs, stream_mode="values"):
                print_last_message(step)
                final_state = step  # her adımda güncelle, son adım kalır

            if final_state:
                # Favori listesini güncelle
                favorites = final_state.get("favorites", favorites)
                # Konuşma geçmişini güncelle — memory_agent.py ile aynı
                conversation_history = list(final_state.get("messages", conversation_history))

        except Exception as e:
            print(f"\n⚠️  Hata: {e}")
            import traceback
            traceback.print_exc()
            print("Tekrar dene.")