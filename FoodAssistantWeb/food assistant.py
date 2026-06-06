"""
Yemek Asistanı - LangGraph + Groq + Gradio + SQLite
Colab'da çalıştırmak için:
1. pip install langchain-groq langgraph gradio
2. GROQ_API_KEY'i gir
3. Çalıştır
"""

import os
import re
import sqlite3
import json
import gradio as gr
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

# ─── CONFIG ──────────────────────────────────────────────────────────────────

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")  # Colab'da secrets'tan al
MODEL_NAME   = "gemma2-9b-it"                        # Groq'ta mevcut Gemma
DB_PATH      = "favorites.db"

SYSTEM_PROMPT = """Sen yardımsever bir Türk yemek asistanısın.

VARSAYILAN TERCİHLER:
- Kişi sayısı: 3
- Öğün: Akşam yemeği
- Tarz: Ev yemeği (pratik, hafif, fit)
- Tercihler: Düşük kalorili, proteinli, glutensiz, sebze ağırlıklı, tavuk veya dana eti, fırın veya tencere yemekleri

KESİNLİKLE ÖNERİLMEYECEKLER:
- Kuzu eti, Uzakdoğu mutfağı, Noodle, Soya sosu, Teriyaki, Sushi, Ramen, Wok tarzı yemekler

YEMEK ÖNERİSİ KURALLARI:
"Ne yiyelim", "yemek öner", "akşam yemeği", "bugün ne yesek" gibi sorular geldiğinde MUTLAKA aşağıdaki formatta JSON döndür.
Başka hiçbir şey yazma, sadece JSON:

{
  "type": "meal_suggestion",
  "categories": {
    "tavuk": ["Yemek 1", "Yemek 2"],
    "dana_et": ["Yemek 1", "Yemek 2"],
    "sebze": ["Yemek 1", "Yemek 2"],
    "bakliyat": ["Yemek 1", "Yemek 2"],
    "fit_salata": ["Yemek 1", "Yemek 2"],
    "balik": ["Yemek 1", "Yemek 2"]
  }
}

Her kategoride tam olarak 3 öneri ver. Türkçe yemek isimleri kullan.

Yemekle ilgili OLMAYAN sorularda normal, yardımsever bir asistan olarak cevap ver (JSON kullanma).
"""

CATEGORY_LABELS = {
    "tavuk":      "🍗 Tavuk Ağırlıklı",
    "dana_et":    "🥩 Dana / Et Ağırlıklı",
    "sebze":      "🥦 Sebze Ağırlıklı",
    "bakliyat":   "🫘 Bakliyat / Proteinli",
    "fit_salata": "🥗 Fit & Hafif / Salatalar",
    "balik":      "🐟 Balık Ağırlıklı",
}

# ─── DATABASE ────────────────────────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def add_favorite(name: str) -> str:
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT OR IGNORE INTO favorites (name) VALUES (?)", (name,))
        conn.commit()
        conn.close()
        return f"✅ **{name}** favorilere eklendi."
    except Exception as e:
        return f"❌ Hata: {e}"

def get_favorites() -> list[str]:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT name FROM favorites ORDER BY id DESC").fetchall()
    conn.close()
    return [r[0] for r in rows]

def remove_favorite(name: str) -> str:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM favorites WHERE name = ?", (name,))
    conn.commit()
    conn.close()
    return f"🗑️ **{name}** favorilerden kaldırıldı."

# ─── LANGGRAPH STATE ─────────────────────────────────────────────────────────

class AgentState(TypedDict):
    messages: list
    response_text: str
    meal_data: dict | None

# ─── NODES ───────────────────────────────────────────────────────────────────

def call_llm(state: AgentState) -> AgentState:
    llm = ChatGroq(
        api_key=GROQ_API_KEY,
        model=MODEL_NAME,
        temperature=0.7,
        max_tokens=1024,
    )
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm.invoke(messages)
    raw = response.content.strip()

    # JSON mu?
    meal_data = None
    try:
        # Bazen model ```json ``` bloğu içine alır, temizle
        clean = re.sub(r"```json|```", "", raw).strip()
        parsed = json.loads(clean)
        if parsed.get("type") == "meal_suggestion":
            meal_data = parsed["categories"]
            raw = "__MEAL_SUGGESTION__"
    except Exception:
        pass

    return {**state, "response_text": raw, "meal_data": meal_data}

def build_graph():
    g = StateGraph(AgentState)
    g.add_node("llm", call_llm)
    g.set_entry_point("llm")
    g.add_edge("llm", END)
    return g.compile()

graph = None

def get_graph():
    global graph
    if graph is None:
        graph = build_graph()
    return graph

# ─── GRADIO HELPERS ──────────────────────────────────────────────────────────

def build_meal_html(categories: dict) -> str:
    """Kategori bazlı yemek önerilerini HTML kartlar olarak render et."""
    html = "<div style='display:flex;flex-direction:column;gap:16px;padding:8px 0'>"
    for key, label in CATEGORY_LABELS.items():
        items = categories.get(key, [])
        if not items:
            continue
        html += f"""
        <div style='background:#1e1e2e;border:1px solid #313244;border-radius:12px;padding:16px'>
          <div style='font-weight:700;font-size:15px;margin-bottom:10px;color:#cdd6f4'>{label}</div>
          <div style='display:flex;flex-direction:column;gap:8px'>
        """
        for item in items:
            safe = item.replace('"', '&quot;').replace("'", "&#39;")
            html += f"""
            <div style='display:flex;justify-content:space-between;align-items:center;
                        background:#181825;border-radius:8px;padding:8px 12px'>
              <span style='color:#cdd6f4;font-size:14px'>{item}</span>
              <button onclick="addFavorite('{safe}')"
                style='background:none;border:none;cursor:pointer;font-size:18px;
                       line-height:1;padding:2px 4px;border-radius:4px;
                       transition:transform 0.15s'
                title='Favorilere ekle'
                onmouseover="this.style.transform='scale(1.3)'"
                onmouseout="this.style.transform='scale(1)'">⭐</button>
            </div>
            """
        html += "</div></div>"
    html += "</div>"
    return html

def favorites_html(favs: list[str]) -> str:
    if not favs:
        return "<p style='color:#6c7086;padding:16px'>Henüz favori yemek eklenmedi.</p>"
    html = "<div style='display:flex;flex-direction:column;gap:8px;padding:8px 0'>"
    for fav in favs:
        safe = fav.replace('"', '&quot;').replace("'", "&#39;")
        html += f"""
        <div style='display:flex;justify-content:space-between;align-items:center;
                    background:#1e1e2e;border:1px solid #313244;border-radius:8px;padding:10px 14px'>
          <span style='color:#cdd6f4'>⭐ {fav}</span>
          <button onclick="removeFavorite('{safe}')"
            style='background:none;border:none;cursor:pointer;color:#f38ba8;
                   font-size:14px;font-weight:600;padding:2px 6px;border-radius:4px'
            title='Kaldır'>✕</button>
        </div>
        """
    html += "</div>"
    return html

# ─── CHAT LOGIC ──────────────────────────────────────────────────────────────

def chat(user_msg: str, history: list, fav_state: list) -> tuple:
    """Ana chat fonksiyonu. Returns: (history, chatbot, fav_state, fav_html, status)"""
    if not GROQ_API_KEY:
        history.append({"role": "assistant", "content": "⚠️ GROQ_API_KEY ayarlanmamış."})
        return history, history, fav_state, favorites_html(fav_state), ""

    # LangGraph mesaj geçmişi
    lc_messages = []
    for msg in history:
        if msg["role"] == "user":
            lc_messages.append(HumanMessage(content=msg["content"]))
        else:
            if msg["content"] != "__MEAL_SUGGESTION__":
                lc_messages.append(AIMessage(content=msg["content"]))
    lc_messages.append(HumanMessage(content=user_msg))

    state = {"messages": lc_messages, "response_text": "", "meal_data": None}
    result = get_graph().invoke(state)

    history.append({"role": "user", "content": user_msg})

    if result["meal_data"]:
        meal_html = build_meal_html(result["meal_data"])
        history.append({"role": "assistant", "content": meal_html})
    else:
        history.append({"role": "assistant", "content": result["response_text"]})

    return history, history, fav_state, favorites_html(fav_state), ""

def handle_add_favorite(name: str, fav_state: list) -> tuple:
    if name and name not in fav_state:
        fav_state = [name] + fav_state
        add_favorite(name)
    return fav_state, favorites_html(fav_state), f"✅ {name} favorilere eklendi"

def handle_remove_favorite(name: str, fav_state: list) -> tuple:
    fav_state = [f for f in fav_state if f != name]
    remove_favorite(name)
    return fav_state, favorites_html(fav_state), f"🗑️ {name} kaldırıldı"

# ─── GRADIO UI ───────────────────────────────────────────────────────────────

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&display=swap');

* { box-sizing: border-box; }
body, .gradio-container { 
    background: #11111b !important; 
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    color: #cdd6f4 !important;
}
.gr-tab-nav { background: #181825 !important; border-bottom: 1px solid #313244 !important; }
.gr-tab-item { color: #6c7086 !important; font-weight: 600 !important; }
.gr-tab-item.selected { color: #89b4fa !important; border-bottom: 2px solid #89b4fa !important; }

footer { display: none !important; }

#chat-col { background: #181825; border-radius: 16px; padding: 16px; }
#fav-col  { background: #181825; border-radius: 16px; padding: 16px; }

.message.user     { background: #313244 !important; color: #cdd6f4 !important; border-radius: 12px !important; }
.message.bot      { background: #1e1e2e !important; color: #cdd6f4 !important; border-radius: 12px !important; }

#send-btn {
    background: linear-gradient(135deg, #89b4fa, #b4befe) !important;
    color: #11111b !important; font-weight: 700 !important;
    border: none !important; border-radius: 10px !important;
}
#send-btn:hover { opacity: 0.9 !important; }

#input-box textarea {
    background: #1e1e2e !important; color: #cdd6f4 !important;
    border: 1px solid #313244 !important; border-radius: 10px !important;
}

.title-bar {
    text-align: center; padding: 20px 0 8px;
    font-size: 26px; font-weight: 700; color: #89b4fa;
    letter-spacing: -0.5px;
}
.subtitle { text-align:center; color:#6c7086; font-size:13px; margin-bottom:12px; }
.status-msg { font-size: 12px; color: #a6e3a1; min-height: 18px; padding: 2px 0; }
"""

JS_BRIDGE = """
<script>
function addFavorite(name) {
    // Gradio'nun hidden input'una yaz ve click tetikle
    const inp = document.getElementById('fav-add-input');
    if (inp) {
        const nativeInput = inp.querySelector('input') || inp.querySelector('textarea');
        if (nativeInput) {
            Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')
                .set.call(nativeInput, name);
            nativeInput.dispatchEvent(new Event('input', { bubbles: true }));
        }
    }
    setTimeout(() => {
        const btn = document.getElementById('fav-add-btn');
        if (btn) btn.click();
    }, 100);
}

function removeFavorite(name) {
    const inp = document.getElementById('fav-remove-input');
    if (inp) {
        const nativeInput = inp.querySelector('input') || inp.querySelector('textarea');
        if (nativeInput) {
            Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')
                .set.call(nativeInput, name);
            nativeInput.dispatchEvent(new Event('input', { bubbles: true }));
        }
    }
    setTimeout(() => {
        const btn = document.getElementById('fav-remove-btn');
        if (btn) btn.click();
    }, 100);
}
</script>
"""

def build_ui():
    init_db()
    initial_favs = get_favorites()

    with gr.Blocks(css=CSS, title="Yemek Asistanı") as demo:
        # State
        history_state = gr.State([])
        fav_state     = gr.State(initial_favs)

        gr.HTML(JS_BRIDGE)
        gr.HTML("<div class='title-bar'>🍽️ Yemek Asistanı</div>")
        gr.HTML("<div class='subtitle'>Ne yesek? Sormana gerek yok, sor zaten.</div>")

        with gr.Tabs():
            # ── CHAT TAB ──────────────────────────────────────────────────────
            with gr.Tab("💬 Sohbet"):
                with gr.Column(elem_id="chat-col"):
                    chatbot = gr.Chatbot(
                        label="",
                        height=480,
                        type="messages",
                        render_markdown=False,
                        sanitize_html=False,
                        bubble_full_width=False,
                    )
                    status_box = gr.HTML(elem_classes=["status-msg"])

                    with gr.Row():
                        user_input = gr.Textbox(
                            placeholder="Ne yiyelim bugün? ya da istediğin bir şey sor...",
                            show_label=False,
                            elem_id="input-box",
                            scale=5,
                        )
                        send_btn = gr.Button("Gönder", elem_id="send-btn", scale=1)

            # ── FAVORİLER TAB ─────────────────────────────────────────────────
            with gr.Tab("⭐ Favoriler"):
                with gr.Column(elem_id="fav-col"):
                    gr.HTML("<div style='font-weight:700;font-size:16px;color:#89b4fa;margin-bottom:12px'>Favori Yemeklerim</div>")
                    fav_display = gr.HTML(favorites_html(initial_favs))
                    fav_status  = gr.HTML(elem_classes=["status-msg"])

        # ── Hidden controls for JS bridge ────────────────────────────────────
        fav_add_input    = gr.Textbox(visible=False, elem_id="fav-add-input")
        fav_add_btn      = gr.Button(visible=False, elem_id="fav-add-btn")
        fav_remove_input = gr.Textbox(visible=False, elem_id="fav-remove-input")
        fav_remove_btn   = gr.Button(visible=False, elem_id="fav-remove-btn")

        # ── Events ───────────────────────────────────────────────────────────
        def submit(msg, hist, favs):
            if not msg.strip():
                return hist, hist, favs, favorites_html(favs), ""
            return chat(msg, hist, favs)

        send_btn.click(
            fn=submit,
            inputs=[user_input, history_state, fav_state],
            outputs=[history_state, chatbot, fav_state, fav_display, status_box],
        ).then(lambda: "", outputs=user_input)

        user_input.submit(
            fn=submit,
            inputs=[user_input, history_state, fav_state],
            outputs=[history_state, chatbot, fav_state, fav_display, status_box],
        ).then(lambda: "", outputs=user_input)

        fav_add_btn.click(
            fn=handle_add_favorite,
            inputs=[fav_add_input, fav_state],
            outputs=[fav_state, fav_display, fav_status],
        ).then(lambda: "", outputs=fav_add_input)

        fav_remove_btn.click(
            fn=handle_remove_favorite,
            inputs=[fav_remove_input, fav_state],
            outputs=[fav_state, fav_display, fav_status],
        ).then(lambda: "", outputs=fav_remove_input)

    return demo

# ─── ENTRY ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not GROQ_API_KEY:
        print("⚠️  GROQ_API_KEY bulunamadı. Lütfen ortam değişkeni olarak ayarla.")
    demo = build_ui()
    demo.launch(share=True, debug=False)