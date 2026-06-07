import re

def update_app_js(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Update Tabs Logic
    content = content.replace("document.querySelectorAll('.tab')", "document.querySelectorAll('.nav-item')")
    
    # 2. Add loadHomeFeed logic right before the // ── INIT ── line
    home_feed_logic = """
// ── HOME FEED ──────────────────────────────────────────────────────────────
async function loadHomeFeed() {
  const featCont = document.getElementById('home-featured-container');
  const altCont = document.getElementById('home-alternatives-container');
  
  featCont.innerHTML = '<div style="text-align:center; padding: 40px; color: var(--muted);">Yükleniyor...</div>';
  altCont.innerHTML = '';

  const res = await apiCall('/api/home-feed');
  if (!res) return;

  const f = res.featured;
  if (f) {
    const badge = f.source === 'plan' ? '<span style="background: var(--accent); padding: 2px 8px; border-radius: 12px; font-size: 10px; margin-left: 10px;">Planda</span>' : '';
    // Generate a quick dummy image based on name for visual effect
    const imgUrl = "https://source.unsplash.com/800x600/?food,turkish," + encodeURIComponent(f.name);
    
    featCont.innerHTML = `
      <div class="featured-card">
        <img src="${imgUrl}" class="featured-img" onerror="this.src='https://source.unsplash.com/800x600/?meal'" alt="${f.name}">
        <div class="featured-content">
          <div class="featured-title">${f.name} ${badge}</div>
          <div class="featured-desc">${f.description}</div>
          <div class="featured-meta">
            <span>⏱️ ${f.time}</span>
            <span>💪 ${f.difficulty}</span>
          </div>
          <div class="featured-btn-row">
            <button class="featured-btn" onclick="openRecipe('${f.name}')">Tarife Git</button>
            <button class="icon-btn" style="background:rgba(255,255,255,0.2); border:none; color:white;" onclick="addFav('${f.name}')">⭐</button>
          </div>
        </div>
      </div>
    `;
  }

  if (res.alternatives && res.alternatives.length > 0) {
    const listHtml = res.alternatives.map(a => {
      const img = "https://source.unsplash.com/150x150/?food,turkish," + encodeURIComponent(a.name);
      return `
      <div class="alt-card" onclick="openRecipe('${a.name}')">
        <img src="${img}" class="alt-img" onerror="this.src='https://source.unsplash.com/150x150/?food'">
        <div class="alt-info">
          <div class="alt-title">${a.name}</div>
          <div class="alt-desc">${a.description}</div>
          <div class="alt-meta"><span>⏱️ ${a.time}</span><span>💪 ${a.difficulty}</span></div>
        </div>
        <button class="icon-btn" style="width:32px;height:32px;background:none;border:none;margin:auto 0;" onclick="event.stopPropagation(); addFav('${a.name}')">⭐</button>
      </div>
      `;
    }).join('');
    altCont.innerHTML = `<div class="alt-list">${listHtml}</div>`;
  }
}

// Search bar integration in Home
document.getElementById('home-search-input').addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && e.target.value.trim() !== '') {
    const val = e.target.value.trim();
    e.target.value = '';
    // Switch to Chat tab and send
    document.querySelector('.nav-item[data-tab="chat"]').click();
    document.getElementById('msg-input').value = val;
    sendMessage();
  }
});
"""
    
    # Insert before INIT
    if "// ── INIT ──" in content:
        content = content.replace("// ── INIT ──", home_feed_logic + "\n// ── INIT ──")
    
    # 3. Call loadHomeFeed() inside INIT block
    # Search for loadData() and insert loadHomeFeed() right after it
    if "loadData();" in content:
        content = content.replace("loadData();", "loadData();\n  loadHomeFeed();")

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == "__main__":
    update_app_js(r"c:\Users\erdem\Desktop\AI Projeler\FoodAssistantWeb\static\app.js")
