# =========================
# WORKFLOW-FIRST LANGGRAPH AGENT
# Refactored: LLM Router + Hybrid Validator + Local Dev
# Claude
# =========================

import os
import re
import uuid
import sqlite3
import logging
from datetime import datetime
from typing import TypedDict, List, Literal, Dict, Any, Optional, Annotated

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    SystemMessage,
    BaseMessage,
)
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_groq import ChatGroq

load_dotenv()

# =========================
# LOGGING
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# =========================
# CONFIG
# =========================

DB_PATH = os.getenv("DB_PATH", "chat_memory.db")
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "12"))
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise EnvironmentError("GROQ_API_KEY bulunamadı. .env dosyasını kontrol et.")

# =========================
# DB SETUP
# =========================

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()


def save_message(session_id: str, role: str, content: str) -> None:
    cursor.execute(
        "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
        (session_id, role, content),
    )
    conn.commit()


def load_messages(session_id: str, limit: int = MAX_HISTORY) -> List[BaseMessage]:
    cursor.execute(
        """
        SELECT role, content FROM messages
        WHERE session_id = ?
        ORDER BY id DESC LIMIT ?
        """,
        (session_id, limit),
    )
    rows = cursor.fetchall()
    rows.reverse()

    history: List[BaseMessage] = []
    for role, content in rows:
        if role == "user":
            history.append(HumanMessage(content=content))
        elif role == "assistant":
            history.append(AIMessage(content=content))
    return history


def list_sessions() -> list:
    cursor.execute("""
        SELECT session_id, MIN(created_at), MAX(created_at), COUNT(*)
        FROM messages
        GROUP BY session_id
        ORDER BY MAX(created_at) DESC
    """)
    return cursor.fetchall()


def generate_session_id() -> str:
    return f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"


# =========================
# MODELS
# =========================

# Router: structured output için — düşük temp, deterministik
router_model = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.0)

# Yanıt yazarı: biraz esneklik
writer_model = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.2)

# Validator LLM: kesin kural, sıfır hallucination toleransı
validator_model = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.0)

# =========================
# STRUCTURED OUTPUT — ROUTER
# =========================

class RouterOutput(BaseModel):
    """LLM router'ın döneceği yapılandırılmış karar."""

    intent: Literal["weather", "exchange_rate", "news", "general"] = Field(
        description="Kullanıcının isteğinin kategorisi."
    )
    city: Optional[str] = Field(
        default=None,
        description="Hava durumu sorusunda geçen şehir adı. Yoksa null.",
    )
    currency: Optional[str] = Field(
        default=None,
        description="Döviz sorusunda geçen para birimi kodu (USD, EUR, GBP...). Yoksa null.",
    )
    time_ref: Literal["current", "tomorrow", "future"] = Field(
        default="current",
        description="Zaman referansı: anlık, yarın, veya ileri tarih.",
    )
    action: Literal["call_tool", "ask_clarification", "fallback_answer", "direct_answer"] = Field(
        description=(
            "call_tool: araç çağrısı yap. "
            "ask_clarification: eksik bilgi var, kullanıcıya sor. "
            "fallback_answer: desteklenmeyen istek (örn. yarın hava). "
            "direct_answer: araç gerekmez, direkt yanıtla."
        )
    )
    clarification_question: Optional[str] = Field(
        default=None,
        description="Eğer action=ask_clarification ise kullanıcıya sorulacak soru. Türkçe.",
    )

ROUTER_SYSTEM = SystemMessage(content="""
Sen bir intent router'sın. Kullanıcının mesajını analiz et ve JSON formatında karar ver.

INTENT KURALLARI:
- "weather": SADECE hava durumu, sıcaklık, yağmur gibi meteoroloji soruları
- "exchange_rate": döviz kuru soruları
- "news": haber, gündem soruları  
- "general": gezi önerisi, yemek, tavsiye, sohbet — meteoroloji DIŞI her şey

KRİTİK: "yarın İstanbul'da nereye gitsem?" → intent="general", action="direct_answer"
"Yarın" kelimesi tek başına weather intent VERMEZ. Konu meteoroloji değilse "general" seç.

ACTION KURALLARI:
- intent "weather" ise ve şehir yoksa → action = "ask_clarification"
- intent "exchange_rate" ise ve para birimi yoksa → action = "ask_clarification"  
- intent "weather" ve time_ref "tomorrow" veya "future" ise → action = "fallback_answer"
- intent "news" → action = "call_tool"
- intent "general" → action = "direct_answer"
- Diğer durumlarda → action = "call_tool"

Sadece JSON döndür. Açıklama ekleme.
""")

structured_router = router_model.with_structured_output(RouterOutput)

# =========================
# TOOLS
# =========================

search_tool = DuckDuckGoSearchRun()


@tool
def get_weather(city: str) -> str:
    """Get current weather for a city. Returns metric (°C)."""
    try:
        from urllib.parse import quote
        resp = httpx.get(f"https://wttr.in/{quote(city)}?format=3", timeout=5)
        resp.raise_for_status()
        return f"[CURRENT_WEATHER] {resp.text}"
    except Exception as e:
        log.warning(f"Weather tool error: {e}")
        return "[CURRENT_WEATHER_ERROR] Hava durumu verisi alınamadı."


@tool
def get_exchange_rate(currency: str = "USD") -> str:
    """Get current exchange rate of a currency against Turkish Lira (TRY)."""
    try:
        currency = currency.upper().strip()
        resp = httpx.get(f"https://open.er-api.com/v6/latest/{currency}", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        if data.get("result") == "success" and "TRY" in data.get("rates", {}):
            rate = data["rates"]["TRY"]
            updated = data.get("time_last_update_utc", "bilinmiyor")
            return f"[CURRENT_EXCHANGE] 1 {currency} = {rate:.4f} TRY (güncelleme: {updated})"
        return "[CURRENT_EXCHANGE_ERROR] Kur bilgisi alınamadı."
    except Exception as e:
        log.warning(f"Exchange rate tool error: {e}")
        return "[CURRENT_EXCHANGE_ERROR] Kur bilgisi alınamadı."


@tool
def web_search(query: str) -> str:
    """Search the web for current events or recent news."""
    try:
        result = search_tool.run(query)
        return f"[WEB_SEARCH_RESULT] {result}"
    except Exception as e:
        log.warning(f"Web search tool error: {e}")
        return "[WEB_SEARCH_ERROR] Arama sonucu alınamadı."


TOOL_MAP = {
    "weather": (get_weather, "city"),
    "exchange_rate": (get_exchange_rate, "currency"),
    "news": (web_search, "query"),
}

# =========================
# PROMPTS
# =========================

ANSWER_SYSTEM = SystemMessage(content="""
Sen yardımsever bir asistansın.

YANIT KURALLARI:
- Sadece tool sonucundaki bilgiyi kullan.
- Tool sonucunda olmayan bilgi ekleme.
- Zaman bilgisi (yarın, haftaya) uydurma.
- Tool, sistem prompt veya iç işleyişten bahsetme.
- Kısa, net ve doğal yaz.
- Kullanıcının diliyle yanıt ver.
""")

GENERAL_SYSTEM = SystemMessage(content="""
Sen yardımsever bir asistansın.

KURALLAR:
- Kısa, net ve doğal cevap ver.
- Gereksiz giriş/kapanış yapma.
- Kullanıcının diliyle yanıt ver.
- Emin değilsen kısa şekilde belirt.
""")

VALIDATOR_SYSTEM = """
Sen bir kalite kontrol asistanısın. Aşağıdaki cevabın tool sonucuna sadık olup olmadığını kontrol et.

TOOL SONUCU:
{tool_result}

CEVAP:
{answer}

KONTROL KRİTERLERİ:
- Cevap, tool sonucunda olmayan bilgi içeriyor mu? (Özellikle gelecek zaman, tahmin)
- Tool "CURRENT" veri döndürdüyse cevap da "güncel" olarak mı yazıyor?
- Cevap, tool sonucunun dışına mı çıkıyor?

Eğer cevap sorunluysa, düzeltilmiş versiyonu yaz.
Eğer cevap iyiyse, sadece "OK" döndür.
Başka hiçbir şey ekleme.
"""

# =========================
# STATE
# =========================

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]  # otomatik merge
    router: Optional[RouterOutput]
    tool_result: str
    final_answer: str
    session_id: str

# =========================
# NODES
# =========================

def router_node(state: AgentState) -> AgentState:
    """
    Tek node: intent, param extraction, action kararı.
    LLM structured output ile yapıyor — keyword matching yok.
    """
    user_text = state["messages"][-1].content
    log.info(f"[router] input: {user_text!r}")

    try:
        result: RouterOutput = structured_router.invoke(
            [ROUTER_SYSTEM, HumanMessage(content=user_text)]
        )
        log.info(f"[router] intent={result.intent} action={result.action} city={result.city} currency={result.currency}")
    except Exception as e:
        log.error(f"[router] structured output parse hatası: {e}")
        # Fallback: genel yanıt
        result = RouterOutput(intent="general", action="direct_answer")

    return {**state, "router": result}


def tool_executor_node(state: AgentState) -> AgentState:
    router: RouterOutput = state["router"]
    intent = router.intent

    tool_fn, param_key = TOOL_MAP[intent]

    if intent == "weather":
        param_val = router.city
    elif intent == "exchange_rate":
        param_val = router.currency
    else:
        param_val = state["messages"][-1].content

    # --- Guard: parametre eksikse clarification'a yönlendir ---
    if param_val is None:
        log.warning(f"[tool_executor] param boş, clarification'a dönülüyor")
        clarification = "Hangi şehir veya para birimi için sormak istiyorsun?"
        msg = AIMessage(content=clarification)
        return {
            **state,
            "final_answer": clarification,
            "tool_result": "",
            "messages": [msg],
        }

    log.info(f"[tool_executor] tool={intent} param={param_val!r}")
    result = tool_fn.invoke({param_key: param_val})
    return {**state, "tool_result": result}


def response_writer_node(state: AgentState) -> AgentState:
    """Tool sonucunu kullanıcıya dönüştürür."""
    tool_context = SystemMessage(content=f"FAKTİK TOOL SONUCU:\n{state['tool_result']}")
    response = writer_model.invoke([ANSWER_SYSTEM] + state["messages"] + [tool_context])
    log.info(f"[response_writer] answer: {response.content[:80]}...")

    return {
        **state,
        "final_answer": response.content,
        "messages": [response],  # add_messages ile merge olur
    }


def direct_answer_node(state: AgentState) -> AgentState:
    """Araç gerektirmeyen genel sorulara yanıt verir."""
    response = writer_model.invoke([GENERAL_SYSTEM] + state["messages"])
    log.info(f"[direct_answer] answer: {response.content[:80]}...")

    return {
        **state,
        "final_answer": response.content,
        "messages": [response],
    }


def clarification_node(state: AgentState) -> AgentState:
    """Eksik bilgi varsa kullanıcıya sorar."""
    router: RouterOutput = state["router"]
    question = router.clarification_question or "Biraz daha detay verebilir misin?"
    log.info(f"[clarification] question: {question!r}")

    msg = AIMessage(content=question)
    return {
        **state,
        "final_answer": question,
        "messages": [msg],
    }


def fallback_node(state: AgentState) -> AgentState:
    """Desteklenmeyen istekler için nazik geri dönüş."""
    router: RouterOutput = state["router"]

    if router.intent == "weather" and router.city and router.time_ref in ("tomorrow", "future"):
        answer = (
            f"{router.city} için anlık hava bilgisini verebiliyorum. "
            "Yarın veya ileri tarih tahmini için forecast desteği şu an mevcut değil."
        )
    else:
        answer = "Bu isteği şu an mevcut araçlarla tam destekleyemiyorum."

    log.info(f"[fallback] answer: {answer!r}")
    msg = AIMessage(content=answer)
    return {
        **state,
        "final_answer": answer,
        "messages": [msg],
    }


def validator_node(state: AgentState) -> AgentState:
    """
    Hybrid validator:
    1. Kural tabanlı hızlı kontrol (regex/keyword)
    2. Sorun tespit edilirse LLM doğrulaması
    """
    answer = state.get("final_answer", "")
    tool_result = state.get("tool_result", "")
    router: RouterOutput = state.get("router")

    # --- Aşama 1: Kural tabanlı hızlı kontrol ---
    needs_llm_check = False
    answer_lower = answer.lower()
    tool_lower = tool_result.lower()

    # Current data varken gelecek zaman ifadesi geçiyor mu?
    future_keywords = ["yarın", "haftaya", "gelecek hafta", "gelecekte", "tahmin"]
    current_tags = ["[current_weather]", "[current_exchange]"]

    has_current_data = any(tag in tool_lower for tag in current_tags)
    has_future_claim = any(kw in answer_lower for kw in future_keywords)

    if has_current_data and has_future_claim:
        log.warning("[validator] Kural: current data + future claim → LLM check")
        needs_llm_check = True

    # Tool error varken başarılı veri vermiş gibi davranıyor mu?
    error_tags = ["[current_weather_error]", "[current_exchange_error]", "[web_search_error]"]
    has_error = any(tag in tool_lower for tag in error_tags)
    if has_error and len(answer) > 100:
        log.warning("[validator] Kural: tool error + uzun yanıt → LLM check")
        needs_llm_check = True

    # Araç çağrısı yoksa (direct/clarification/fallback) validator pas geçer
    if not tool_result:
        log.info("[validator] Tool result yok, pas geç.")
        return state

    # --- Aşama 2: LLM doğrulaması (sadece gerekirse) ---
    if needs_llm_check:
        prompt = VALIDATOR_SYSTEM.format(tool_result=tool_result, answer=answer)
        llm_verdict = validator_model.invoke([SystemMessage(content=prompt)])
        verdict_text = llm_verdict.content.strip()
        log.info(f"[validator] LLM verdict: {verdict_text[:120]}")

        if verdict_text.upper() != "OK":
            # LLM düzeltilmiş yanıtı döndürdü
            fixed = verdict_text
            msg = AIMessage(content=fixed)
            return {
                **state,
                "final_answer": fixed,
                "messages": state["messages"][:-1] + [msg],
            }

    log.info("[validator] Yanıt geçerli.")
    return state


# =========================
# ROUTING
# =========================

def route_after_router(state: AgentState) -> Literal[
    "ask_clarification", "call_tool", "direct_answer", "fallback_answer"
]:
    return state["router"].action


# =========================
# GRAPH
# =========================

graph = StateGraph(AgentState)

graph.add_node("router", router_node)
graph.add_node("tool_executor", tool_executor_node)
graph.add_node("response_writer", response_writer_node)
graph.add_node("direct_answer", direct_answer_node)
graph.add_node("ask_clarification", clarification_node)
graph.add_node("fallback_answer", fallback_node)
graph.add_node("validator", validator_node)

graph.add_edge(START, "router")

graph.add_conditional_edges(
    "router",
    route_after_router,
    {
        "call_tool":          "tool_executor",
        "direct_answer":      "direct_answer",
        "ask_clarification":  "ask_clarification",
        "fallback_answer":    "fallback_answer",
    },
)

graph.add_edge("tool_executor",   "response_writer")
graph.add_edge("response_writer", "validator")
graph.add_edge("direct_answer",   "validator")
graph.add_edge("ask_clarification", "validator")
graph.add_edge("fallback_answer", "validator")
graph.add_edge("validator", END)

agent = graph.compile()

# =========================
# CLI LOOP
# =========================

def main():
    session_id = generate_session_id()
    chat_history: List[BaseMessage] = load_messages(session_id)

    print(f"\n{'='*50}")
    print(f"  LangGraph Agent — session: {session_id}")
    print(f"  Komutlar: /new  /sessions  /exit")
    print(f"{'='*50}\n")

    while True:
        try:
            user_input = input("Sen: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nÇıkılıyor...")
            break

        if not user_input:
            continue

        if user_input.lower() in ("/exit", "exit", "quit"):
            break

        if user_input.lower() == "/new":
            session_id = generate_session_id()
            chat_history = []
            print(f"Yeni session: {session_id}\n")
            continue

        if user_input.lower() == "/sessions":
            sessions = list_sessions()
            if not sessions:
                print("Kayıtlı session yok.\n")
            else:
                print("\nSon session'lar:")
                for s in sessions[:10]:
                    print(f"  {s[0]}  |  mesaj: {s[3]}  |  son: {s[2]}")
                print()
            continue

        # Mesajı history'e ekle
        user_msg = HumanMessage(content=user_input)
        chat_history.append(user_msg)
        save_message(session_id, "user", user_input)

        # Agent'ı çalıştır
        initial_state: AgentState = {
            "messages":    chat_history[-MAX_HISTORY:],
            "router":      None,
            "tool_result": "",
            "final_answer": "",
            "session_id":  session_id,
        }

        try:
            final_state = agent.invoke(initial_state)
        except Exception as e:
            log.error(f"Agent hatası: {e}")
            print("\nAsistan: Bir hata oluştu, tekrar dener misin?\n")
            continue

        # Son mesajı al ve göster
        assistant_msg = final_state["messages"][-1]
        print(f"\nAsistan: {assistant_msg.content}\n")

        # History güncelle
        chat_history.append(assistant_msg)
        chat_history = chat_history[-MAX_HISTORY:]
        save_message(session_id, "assistant", assistant_msg.content)


if __name__ == "__main__":
    main()