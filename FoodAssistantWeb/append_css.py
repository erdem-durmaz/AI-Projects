import re

css_additions = """
/* --- BOTTOM NAV --- */
.bottom-nav {
  position: fixed;
  bottom: 0; left: 0; right: 0;
  display: flex;
  justify-content: space-around;
  background: var(--surface);
  backdrop-filter: var(--backdrop);
  -webkit-backdrop-filter: var(--backdrop);
  border-top: 1px solid var(--border);
  padding: 12px 10px;
  padding-bottom: max(12px, env(safe-area-inset-bottom));
  z-index: 1000;
}
.nav-item {
  display: flex; flex-direction: column; align-items: center; gap: 4px;
  color: var(--muted); cursor: pointer; transition: color 0.15s;
  flex: 1; text-align: center;
}
.nav-item.active { color: var(--accent); }
.nav-icon { font-size: 20px; margin-bottom: 2px; }
.nav-item span { font-size: 11px; font-weight: 600; }

/* --- HOME PANEL --- */
#home-panel { padding-bottom: 100px; overflow-y: auto; }
.home-search-bar { padding: 16px; position: sticky; top: 0; z-index: 50; background: var(--bg); }
.search-input-wrapper {
  display: flex; align-items: center; background: var(--input-bg);
  border: 1.5px solid var(--border); border-radius: 20px; padding: 10px 16px;
  backdrop-filter: var(--backdrop); -webkit-backdrop-filter: var(--backdrop);
}
.search-input-wrapper .search-icon { font-size: 16px; margin-right: 10px; opacity: 0.7; }
#home-search-input { flex: 1; background: transparent; border: none; outline: none; color: var(--text); font-size: 15px; font-family: inherit; }

.home-header { padding: 0 16px; margin-top: 10px; margin-bottom: 16px; }
.greeting { font-size: 15px; color: var(--muted); margin-bottom: 4px; }
.home-header h2 { font-size: 26px; font-weight: 800; letter-spacing: -0.5px; }

.featured-card {
  margin: 0 16px; border-radius: 24px; overflow: hidden; position: relative;
  border: 1px solid var(--border); box-shadow: var(--shadow-lg);
  background: var(--surface);
}
.featured-img { width: 100%; height: 240px; object-fit: cover; display: block; }
.featured-content {
  position: absolute; bottom: 0; left: 0; right: 0;
  padding: 20px;
  background: linear-gradient(to top, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.5) 60%, transparent 100%);
  backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
}
.featured-title { font-size: 22px; font-weight: 800; color: #fff; margin-bottom: 6px; }
.featured-desc { font-size: 13px; color: rgba(255,255,255,0.8); margin-bottom: 14px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.featured-meta { display: flex; gap: 12px; font-size: 12px; color: rgba(255,255,255,0.9); font-weight: 600; margin-bottom: 16px; }
.featured-btn-row { display: flex; gap: 10px; }
.featured-btn { flex: 1; background: linear-gradient(135deg, var(--accent), var(--accent-dark)); color: #fff; border: none; border-radius: 14px; padding: 12px; font-size: 15px; font-weight: 700; cursor: pointer; box-shadow: 0 4px 15px rgba(249, 115, 22, 0.4); }

.alt-list { display: flex; flex-direction: column; gap: 12px; padding: 0 16px; }
.alt-card { display: flex; gap: 12px; background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 12px; backdrop-filter: var(--backdrop); -webkit-backdrop-filter: var(--backdrop); box-shadow: var(--shadow); cursor: pointer; }
.alt-img { width: 72px; height: 72px; border-radius: 12px; object-fit: cover; background: var(--border); flex-shrink: 0; }
.alt-info { flex: 1; display: flex; flex-direction: column; justify-content: center; min-width: 0; }
.alt-title { font-size: 16px; font-weight: 700; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.alt-desc { font-size: 12px; color: var(--muted); margin-bottom: 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.alt-meta { display: flex; gap: 10px; font-size: 11px; font-weight: 600; color: var(--muted); }

/* Padding for panels to clear bottom nav */
.panel { padding-bottom: 90px; }
.input-area { bottom: 70px; position: fixed; left: 0; right: 0; }
"""

def update_css(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Hide .tabs entirely
    content = content.replace('.tabs { display: flex;', '.tabs { display: none;')
    
    # Append new CSS
    content += "\n" + css_additions
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == "__main__":
    update_css(r"c:\Users\erdem\Desktop\AI Projeler\FoodAssistantWeb\static\styles.css")
