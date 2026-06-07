// ── STATE ──────────────────────────────────────────────────────────────────
const S = {
  history: [],
  favorites: [],
  chefSpecials: [],
  plan: {},
  days: [],
  preferences: {},
  myRecipes: [],
  loading: false,
};

const DAYS_TR = ["Pazartesi","Salı","Çarşamba","Perşembe","Cuma","Cumartesi","Pazar"];

function todayName() {
  const d = new Date().getDay();
  const map = [6,0,1,2,3,4,5];
  return DAYS_TR[map[d]];
}

function esc(text) {
  const el = document.createElement('span');
  el.textContent = text;
  return el.innerHTML;
}

// ── API ────────────────────────────────────────────────────────────────────
async function api(path, body) {
  const opts = body
    ? { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body) }
    : { method:'GET' };
  const res = await fetch(path, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ── THEME ──────────────────────────────────────────────────────────────────
function initTheme() {
  const saved = localStorage.getItem('theme');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const theme = saved || (prefersDark ? 'dark' : 'light');
  document.documentElement.setAttribute('data-theme', theme);
}

function toggleTheme() {
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  const next = isDark ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('theme', next);
}

// ── TOAST ──────────────────────────────────────────────────────────────────
let _tt;
function toast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(_tt);
  _tt = setTimeout(() => el.classList.remove('show'), 2200);
}

// ── TABS ───────────────────────────────────────────────────────────────────
document.querySelectorAll('.nav-item').forEach(t => t.addEventListener('click', () => {
  document.querySelectorAll('.nav-item').forEach(x => x.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(x => x.classList.remove('active'));
  t.classList.add('active');
  document.getElementById(t.dataset.tab + '-panel').classList.add('active');
}));

// ── WEEK GRID ──────────────────────────────────────────────────────────────
function getPlanMeals(day) {
  const val = S.plan[day];
  if (Array.isArray(val)) return val;
  if (val) return [val];
  return [];
}

function renderWeekGrid() {
  const grid = document.getElementById('week-grid');
  grid.innerHTML = '';
  const today = todayName();

  S.days.forEach(day => {
    const meals = getPlanMeals(day);
    const isToday = day === today;
    const slot = document.createElement('div');
    slot.className = 'day-slot' + (meals.length ? ' has-meal' : '') + (isToday ? ' today' : '');
    slot.dataset.day = day;

    const label = document.createElement('div');
    label.className = 'day-label';
    label.innerHTML = `${esc(day)}${isToday ? '<span class="today-badge">Bugün</span>' : ''}`;
    slot.appendChild(label);

    if (meals.length) {
      const list = document.createElement('div');
      list.className = 'day-meals';
      meals.forEach(meal => {
        const chip = document.createElement('span');
        chip.className = 'meal-chip';
        chip.innerHTML = `<span class="meal-chip-name">${esc(meal)}</span><button class="meal-chip-remove" title="Kaldır">×</button>`;
        chip.querySelector('.meal-chip-remove').addEventListener('click', async e => {
          e.stopPropagation();
          const res = await api('/plan/remove', { day, meal });
          S.plan = res.plan;
          renderWeekGrid();
        });
        list.appendChild(chip);
      });
      slot.appendChild(list);
    } else {
      const empty = document.createElement('div');
      empty.className = 'day-empty';
      empty.textContent = 'Yemek ekle';
      slot.appendChild(empty);
    }

    const clearBtn = document.createElement('button');
    clearBtn.className = 'day-remove';
    clearBtn.title = 'Günü temizle';
    clearBtn.textContent = '×';
    if (meals.length) {
      clearBtn.addEventListener('click', async () => {
        const res = await api('/plan/clear-day', { day });
        S.plan = res.plan;
        renderWeekGrid();
      });
    }
    slot.appendChild(clearBtn);

    slot.addEventListener('dragover', e => { e.preventDefault(); slot.classList.add('drag-over'); });
    slot.addEventListener('dragleave', () => slot.classList.remove('drag-over'));
    slot.addEventListener('drop', async e => {
      e.preventDefault();
      slot.classList.remove('drag-over');
      const name = e.dataTransfer.getData('text/plain');
      if (!name) return;
      if (getPlanMeals(day).includes(name)) {
        toast(`${name} zaten ${day} planında`);
        return;
      }
      const res = await api('/plan/add', { day, meal: name });
      S.plan = res.plan;
      renderWeekGrid();
      toast(`📅 ${day}: ${name} eklendi`);
    });
    grid.appendChild(slot);
  });
}

document.getElementById('clear-plan-btn').addEventListener('click', async () => {
  if (!confirm('Haftalık planı temizlemek istediğinden emin misin?')) return;
  const res = await api('/plan/clear');
  S.plan = res.plan;
  renderWeekGrid();
  toast('Plan temizlendi');
});

// ── FAVORITES ──────────────────────────────────────────────────────────────
function renderFavorites() {
  const list  = document.getElementById('fav-list');
  const empty = document.getElementById('fav-empty');
  const count = document.getElementById('fav-count');
  const badge = document.getElementById('fav-badge');
  list.innerHTML = '';
  const n = S.favorites.length;
  count.textContent = n;
  if (badge) badge.textContent = n > 0 ? ` (${n})` : '';
  empty.style.display = n === 0 ? 'block' : 'none';
  list.style.display  = n === 0 ? 'none'  : 'flex';

  S.favorites.forEach(name => {
    const item = document.createElement('div');
    item.className = 'fav-item';
    item.dataset.name = name;
    item.draggable = true;
    const isChef = S.chefSpecials.includes(name);
    item.innerHTML = `
      <span class="drag-handle">☰</span>
      <span class="fav-name">${esc(name)}</span>
      <button class="fav-plan-btn plan-btn" title="Plana ekle">📅</button>
      <button class="fav-recipe-btn recipe-btn" title="Tarifi gör">📖</button>
      <button class="fav-chef-btn chef-btn ${isChef ? 'added' : ''}" title="Şefin Spesyali">${isChef ? '👑' : '👨‍🍳'}</button>
      <button class="remove-btn" title="Kaldır">×</button>
    `;
    item.querySelector('.remove-btn').addEventListener('click', () => removeFavorite(name));
    item.querySelector('.fav-plan-btn').addEventListener('click', e => { e.stopPropagation(); openDayModal(name); });
    item.querySelector('.fav-recipe-btn').addEventListener('click', e => { e.stopPropagation(); openRecipeByName(name); });
    item.querySelector('.fav-chef-btn').addEventListener('click', e => {
      e.stopPropagation();
      toggleChef(name, e.currentTarget);
    });
    item.addEventListener('dragstart', e => {
      e.dataTransfer.setData('text/plain', name);
      e.dataTransfer.effectAllowed = 'copy';
      document.getElementById('fav-drop-zone').style.display = 'block';
      document.getElementById('chef-drop-zone').style.display = 'block';
    });
    item.addEventListener('dragend', () => {
      document.getElementById('fav-drop-zone').style.display = 'none';
      document.getElementById('chef-drop-zone').style.display = 'none';
    });
    list.appendChild(item);
  });

  if (window._favSort) window._favSort.destroy();
  window._favSort = Sortable.create(list, {
    animation: 180,
    handle: '.drag-handle',
    ghostClass: 'sortable-ghost',
    chosenClass: 'sortable-chosen',
    onEnd: async () => {
      const newOrder = [...list.querySelectorAll('.fav-item')].map(el => el.dataset.name);
      S.favorites = newOrder;
      await api('/favorites/reorder', { names: newOrder });
    }
  });
}

// ── CHEF'S SPECIALS ────────────────────────────────────────────────────────
function renderChefSpecials() {
  const list  = document.getElementById('chef-list');
  const empty = document.getElementById('chef-empty');
  const count = document.getElementById('chef-count');
  list.innerHTML = '';
  const n = S.chefSpecials.length;
  count.textContent = n;
  empty.style.display = n === 0 ? 'block' : 'none';
  list.style.display  = n === 0 ? 'none'  : 'flex';

  S.chefSpecials.forEach(name => {
    const item = document.createElement('div');
    item.className = 'fav-item chef-special-item';
    item.dataset.name = name;
    item.draggable = true;
    const isFav = S.favorites.includes(name);
    item.innerHTML = `
      <span class="drag-handle">☰</span>
      <span class="fav-name">${esc(name)}</span>
      <button class="fav-plan-btn plan-btn" title="Plana ekle">📅</button>
      <button class="fav-recipe-btn recipe-btn" title="Tarifi gör">📖</button>
      <button class="fav-star-btn add-btn ${isFav ? 'added' : ''}" title="Favorilere ekle/çıkar">${isFav ? '✅' : '⭐'}</button>
      <button class="remove-btn" title="Kaldır">×</button>
    `;
    item.querySelector('.remove-btn').addEventListener('click', () => removeChefSpecial(name));
    item.querySelector('.fav-plan-btn').addEventListener('click', e => { e.stopPropagation(); openDayModal(name); });
    item.querySelector('.fav-recipe-btn').addEventListener('click', e => { e.stopPropagation(); openRecipeByName(name); });
    item.querySelector('.fav-star-btn').addEventListener('click', e => {
      e.stopPropagation();
      toggleFav(name, e.currentTarget);
    });
    item.addEventListener('dragstart', e => {
      e.dataTransfer.setData('text/plain', name);
      e.dataTransfer.effectAllowed = 'copy';
      document.getElementById('fav-drop-zone').style.display = 'block';
      document.getElementById('chef-drop-zone').style.display = 'block';
    });
    item.addEventListener('dragend', () => {
      document.getElementById('fav-drop-zone').style.display = 'none';
      document.getElementById('chef-drop-zone').style.display = 'none';
    });
    list.appendChild(item);
  });

  if (window._chefSort) window._chefSort.destroy();
  window._chefSort = Sortable.create(list, {
    animation: 180,
    handle: '.drag-handle',
    ghostClass: 'sortable-ghost',
    chosenClass: 'sortable-chosen',
    onEnd: async () => {
      const newOrder = [...list.querySelectorAll('.chef-special-item')].map(el => el.dataset.name);
      S.chefSpecials = newOrder;
      await api('/chef-specials/reorder', { names: newOrder });
    }
  });
}

const dropZone = document.getElementById('fav-drop-zone');
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', async e => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  dropZone.style.display = 'none';
  const name = e.dataTransfer.getData('text/plain');
  if (name) await addFavorite(name);
});

const chefDropZone = document.getElementById('chef-drop-zone');
chefDropZone.addEventListener('dragover', e => { e.preventDefault(); chefDropZone.classList.add('drag-over'); });
chefDropZone.addEventListener('dragleave', () => chefDropZone.classList.remove('drag-over'));
chefDropZone.addEventListener('drop', async e => {
  e.preventDefault();
  chefDropZone.classList.remove('drag-over');
  chefDropZone.style.display = 'none';
  const name = e.dataTransfer.getData('text/plain');
  if (name) await addChefSpecial(name);
});

async function addFavorite(name) {
  if (S.favorites.includes(name)) { toast(`${name} zaten favorilerde`); return; }
  const res = await api('/favorites/add', { name });
  S.favorites = res.favorites;
  renderFavorites();
  renderChefSpecials();
  toast(`⭐ ${name} eklendi`);
}

async function removeFavorite(name) {
  const res = await api('/favorites/remove', { name });
  S.favorites = res.favorites;
  renderFavorites();
  renderChefSpecials();
  toast(`🗑 ${name} kaldırıldı`);
}

async function addChefSpecial(name) {
  if (S.chefSpecials.includes(name)) { toast(`${name} zaten şefin spesyallerinde`); return; }
  const res = await api('/chef-specials/add', { name });
  S.chefSpecials = res.chef_specials;
  renderChefSpecials();
  renderFavorites();
  toast(`👨‍🍳 ${name} şefin spesyali yapıldı`);
}

async function removeChefSpecial(name) {
  const res = await api('/chef-specials/remove', { name });
  S.chefSpecials = res.chef_specials;
  renderChefSpecials();
  renderFavorites();
  toast(`🗑 ${name} şefin spesyallerinden kaldırıldı`);
}

// ── ÖNER ───────────────────────────────────────────────────────────────────
const msgEl  = document.getElementById('messages');
const msgEmpty = document.getElementById('messages-empty');
const inp    = document.getElementById('msg-input');
const sendB  = document.getElementById('send-btn');

inp.addEventListener('input', function() {
  this.style.height = 'auto';
  this.style.height = Math.min(this.scrollHeight, 110) + 'px';
});
inp.addEventListener('keydown', e => { if (e.key==='Enter' && !e.shiftKey) { e.preventDefault(); send(); } });
sendB.addEventListener('click', send);

function scrollBot() { setTimeout(() => msgEl.scrollTop = msgEl.scrollHeight, 40); }

function hideEmptyState() {
  if (msgEmpty) msgEmpty.style.display = 'none';
}

function addUserMsg(text) {
  hideEmptyState();
  const wrapper = document.createElement('div');
  wrapper.className = 'msg-wrapper user';
  const d = document.createElement('div');
  d.className = 'msg user';
  d.textContent = text;
  wrapper.appendChild(d);
  msgEl.appendChild(wrapper);
  scrollBot();
  return wrapper;
}

function addBotMsg(text) {
  hideEmptyState();
  const wrapper = document.createElement('div');
  wrapper.className = 'msg-wrapper bot';
  const d = document.createElement('div');
  d.className = 'msg bot';
  d.textContent = text;
  wrapper.appendChild(d);
  msgEl.appendChild(wrapper);
  scrollBot();
  return d;
}

function addTyping() {
  const wrapper = document.createElement('div');
  wrapper.className = 'msg-wrapper bot';
  wrapper.id = 'typing-indicator';
  const d = document.createElement('div');
  d.className = 'msg bot typing';
  d.textContent = 'Öneriler hazırlanıyor...';
  wrapper.appendChild(d);
  msgEl.appendChild(wrapper);
  scrollBot();
  return wrapper;
}

function removeTyping() {
  document.getElementById('typing-indicator')?.remove();
}

function addMealCards(data) {
  hideEmptyState();
  const wrapper = document.createElement('div');
  wrapper.className = 'meal-card-wrapper';
  const intro = document.createElement('div');
  intro.className = 'meal-intro';
  intro.textContent = '📖 tarif · ⭐ favori · 👨‍🍳 spesyal · 📅 plana ekle';
  wrapper.appendChild(intro);

  const grid = document.createElement('div');
  grid.className = 'categories-grid';

  for (const [, cat] of Object.entries(data)) {
    const card = document.createElement('div');
    card.className = 'category-card';
    card.innerHTML = `<div class="category-header"><span class="cat-emoji">${cat.emoji}</span><span class="cat-name">${esc(cat.label)}</span></div>`;

    cat.items.forEach(name => {
      const item = document.createElement('div');
      item.className = 'meal-item';
      item.draggable = true;
      item.dataset.name = name;

      const nameEl = document.createElement('span');
      nameEl.className = 'meal-name';
      nameEl.textContent = name;

      const actions = document.createElement('div');
      actions.className = 'meal-actions';

      const recipeBtn = document.createElement('button');
      recipeBtn.className = 'recipe-btn';
      recipeBtn.textContent = '📖';
      recipeBtn.title = 'Tarifi gör';
      recipeBtn.addEventListener('click', e => { e.stopPropagation(); openRecipeByName(name); });

      const planBtn = document.createElement('button');
      planBtn.className = 'plan-btn';
      planBtn.textContent = '📅';
      planBtn.title = 'Plana ekle';
      planBtn.addEventListener('click', e => { e.stopPropagation(); openDayModal(name); });

      const favBtn = document.createElement('button');
      favBtn.className = 'add-btn' + (S.favorites.includes(name) ? ' added' : '');
      favBtn.textContent = S.favorites.includes(name) ? '✅' : '⭐';
      favBtn.title = 'Favori';
      favBtn.addEventListener('click', async () => {
        if (S.favorites.includes(name)) {
          await removeFavorite(name);
          favBtn.classList.remove('added');
          favBtn.textContent = '⭐';
        } else {
          await addFavorite(name);
          favBtn.classList.add('added');
          favBtn.textContent = '✅';
        }
      });

      const chefBtn = document.createElement('button');
      chefBtn.className = 'chef-btn' + (S.chefSpecials.includes(name) ? ' added' : '');
      chefBtn.textContent = S.chefSpecials.includes(name) ? '👑' : '👨‍🍳';
      chefBtn.title = 'Şefin Spesyali';
      chefBtn.addEventListener('click', async () => {
        if (S.chefSpecials.includes(name)) {
          await removeChefSpecial(name);
          chefBtn.classList.remove('added');
          chefBtn.textContent = '👨‍🍳';
        } else {
          await addChefSpecial(name);
          chefBtn.classList.add('added');
          chefBtn.textContent = '👑';
        }
      });

      item.addEventListener('dragstart', e => {
        e.dataTransfer.setData('text/plain', name);
        e.dataTransfer.effectAllowed = 'copy';
        item.classList.add('dragging');
        dropZone.style.display = 'block';
        chefDropZone.style.display = 'block';
      });
      item.addEventListener('dragend', () => {
        item.classList.remove('dragging');
        dropZone.style.display = 'none';
        chefDropZone.style.display = 'none';
      });

      actions.appendChild(recipeBtn);
      actions.appendChild(planBtn);
      actions.appendChild(favBtn);
      actions.appendChild(chefBtn);
      item.appendChild(nameEl);
      item.appendChild(actions);
      card.appendChild(item);
    });
    grid.appendChild(card);
  }
  wrapper.appendChild(grid);
  msgEl.appendChild(wrapper);
  scrollBot();
}

function pushHistory(userMsg, assistantContent) {
  S.history.push({ role:'user', content: userMsg });
  S.history.push({ role:'assistant', content: assistantContent });
}

async function sendStream(msg) {
  addTyping();
  const res = await fetch('/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: msg, history: S.history }),
  });
  if (!res.ok) throw new Error('Öneri alınamadı');

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let partial = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    partial += decoder.decode(value, { stream: true });
    const lines = partial.split('\n');
    partial = lines.pop() || '';

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const data = JSON.parse(line.slice(6));
      if (data.error) throw new Error(data.error);
      if (data.done) {
        removeTyping();
        if (data.type === 'meal') {
          const allMeals = Object.values(data.data).flatMap(cat => cat.items);
          pushHistory(msg, 'Önerilen yemekler: ' + allMeals.join(', ') + '. Bir sonraki istekte bunları tekrar önerme.');
          addMealCards(data.data);
          if (data.usage && data.usage.total_tokens) {
            const u = document.createElement('div');
            u.style = "font-size: 11px; color: var(--text-muted); text-align: right; margin-top: -10px; margin-bottom: 12px; margin-right: 12px;";
            u.innerHTML = `⚡ In: ${data.usage.input_tokens || 0} | Out: ${data.usage.output_tokens || 0} | Total: ${data.usage.total_tokens}`;
            msgEl.appendChild(u);
            scrollBot();
          }
        } else if (data.type === 'action' && data.action === 'open_recipe') {
          pushHistory(msg, `Sistem: ${data.query} tarifi arandı.`);
          const msgNode = addBotMsg(`🔍 ${data.query} aranıyor...`);
          if (data.usage && data.usage.total_tokens) {
            const u = document.createElement('div');
            u.style = "font-size: 11px; color: var(--text-muted); text-align: right; margin-top: 4px;";
            u.innerHTML = `⚡ In: ${data.usage.input_tokens || 0} | Out: ${data.usage.output_tokens || 0} | Total: ${data.usage.total_tokens}`;
            msgNode.parentNode.appendChild(u);
          }
          openRecipeByName(data.query).then(() => {
            msgNode.textContent = `✅ ${data.query} tarifi bulundu ve ekranda açıldı.`;
          }).catch(() => {
            msgNode.textContent = `❌ ${data.query} tarifi bulunamadı.`;
          });
        } else {
          throw new Error(data.error || 'Öneri oluşturulamadı');
        }
        return;
      }
    }
  }
}

async function send() {
  const msg = inp.value.trim();
  if (!msg || S.loading) return;
  S.loading = true;
  sendB.disabled = true;
  inp.value = '';
  inp.style.height = 'auto';
  addUserMsg(msg);
  try {
    await sendStream(msg);
  } catch(e) {
    removeTyping();
    toast('⚠️ ' + (e.message || 'Tekrar dene'));
  }
  S.loading = false;
  sendB.disabled = false;
  inp.focus();
}

// ── DAY MODAL ──────────────────────────────────────────────────────────────
const modalBg    = document.getElementById('day-modal-bg');
const modalLabel = document.getElementById('modal-meal-label');
const modalGrid  = document.getElementById('modal-day-grid');
document.getElementById('modal-cancel').addEventListener('click', () => modalBg.classList.remove('open'));
modalBg.addEventListener('click', e => { if (e.target === modalBg) modalBg.classList.remove('open'); });

function openDayModal(mealName) {
  modalLabel.textContent = mealName;
  modalGrid.innerHTML = '';
  S.days.forEach(day => {
    const current = getPlanMeals(day);
    const already = current.includes(mealName);
    const btn = document.createElement('button');
    btn.className = 'day-pick-btn' + (current.length ? ' has-meal' : '');
    const summary = current.length ? current.join(', ') : '';
    btn.innerHTML = `<span class="day-name">${esc(day)}</span>${summary ? `<span class="day-current">→ ${esc(summary)}</span>` : ''}`;
    btn.addEventListener('click', async () => {
      if (already) {
        toast(`${mealName} zaten ${day} planında`);
        return;
      }
      const res = await api('/plan/add', { day, meal: mealName });
      S.plan = res.plan;
      renderWeekGrid();
      modalBg.classList.remove('open');
      toast(`📅 ${day}: ${mealName} eklendi`);
    });
    modalGrid.appendChild(btn);
  });
  modalBg.classList.add('open');
}

// ── RECIPE DRAWER ──────────────────────────────────────────────────────────
const recipeDrawer  = document.getElementById('recipe-drawer');
const recipeContent = document.getElementById('recipe-content');

document.getElementById('recipe-close').addEventListener('click', closeRecipe);
document.getElementById('recipe-overlay').addEventListener('click', closeRecipe);
function closeRecipe() { recipeDrawer.classList.remove('open'); }

async function openRecipeByName(name) {
  recipeContent.innerHTML = '<div class="search-loading"><span class="spinner">🔄</span>Tarif aranıyor...</div>';
  recipeDrawer.classList.add('open');
  try {
    const recRes = await api('/recipe_by_name', { name });
    const result = recRes.result;
    if (result.type === 'recipe') {
      renderRecipeDrawer(result, name);
    } else if (result.type === 'list') {
      renderListDrawer(result.items, { url: result.source_url || '#', name });
    } else {
      recipeContent.innerHTML = `<div class="recipe-error"><div style="font-size:32px;margin-bottom:8px">🤷</div><p>${esc(result.error || 'Tarif bulunamadı')}</p></div>`;
      throw new Error('Not found');
    }
  } catch(e) {
    recipeContent.innerHTML = '<div class="recipe-error"><div style="font-size:32px;margin-bottom:8px">⚠️</div><p>Yüklenemedi</p></div>';
    throw e;
  }
}

async function openCustomRecipe(id) {
  recipeContent.innerHTML = '<div class="search-loading"><span class="spinner">🔄</span>Yükleniyor...</div>';
  recipeDrawer.classList.add('open');
  try {
    const res = await api(`/my-recipes/${id}`);
    renderRecipeDrawer(res.recipe, res.recipe.name);
  } catch(e) {
    recipeContent.innerHTML = '<div class="recipe-error"><div style="font-size:32px;margin-bottom:8px">⚠️</div><p>Yüklenemedi</p></div>';
  }
}

function renderListDrawer(items, sourceResult) {
  recipeContent.innerHTML = '';
  const closeBtn = document.createElement('button');
  closeBtn.className = 'recipe-close';
  closeBtn.textContent = '×';
  closeBtn.addEventListener('click', closeRecipe);
  recipeContent.appendChild(closeBtn);

  const title = document.createElement('div');
  title.className = 'recipe-title';
  title.style.fontSize = '15px';
  title.textContent = '📋 Bu sayfadaki yemekler';
  recipeContent.appendChild(title);

  const list = document.createElement('div');
  list.style.cssText = 'display:flex;flex-direction:column;gap:8px;margin-top:14px';

  items.forEach(name => {
    const isFav = S.favorites.includes(name);
    const item = document.createElement('div');
    item.className = 'search-item';
    item.style.cursor = 'pointer';
    item.innerHTML = `
      <div style="flex:1"><div class="search-item-name">${esc(name)}</div></div>
      <button class="search-item-star ${isFav ? 'added' : ''}">${isFav ? '✅' : '⭐'}</button>
      <span class="search-item-arrow">›</span>
    `;
    const starBtn = item.querySelector('.search-item-star');
    starBtn.addEventListener('click', async e => {
      e.stopPropagation();
      if (starBtn.classList.contains('added')) return;
      await addFavorite(name);
      starBtn.classList.add('added');
      starBtn.textContent = '✅';
    });
    item.addEventListener('click', () => openRecipeByName(name));
    list.appendChild(item);
  });
  recipeContent.appendChild(list);
}

function renderRecipeDrawer(recipe, fallbackName) {
  const name = recipe.name || fallbackName;
  const isFav = S.favorites.includes(name);
  recipeContent.innerHTML = '';

  const closeBtn = document.createElement('button');
  closeBtn.className = 'recipe-close';
  closeBtn.textContent = '×';
  closeBtn.addEventListener('click', closeRecipe);
  recipeContent.appendChild(closeBtn);

  const cover = document.createElement('img');
  cover.className = 'recipe-cover-image';
  cover.src = `https://tse1.mm.bing.net/th?q=${encodeURIComponent(name)}+yemek+tarifi&w=800&h=600&c=7`;
  recipeContent.appendChild(cover);

  const title = document.createElement('div');
  title.className = 'recipe-title';
  title.textContent = name;
  recipeContent.appendChild(title);

  if (recipe.custom) {
    const badge = document.createElement('div');
    badge.className = 'recipe-meta';
    badge.innerHTML = '<span class="custom-source">📒 Kendi tarifim</span>';
    recipeContent.appendChild(badge);
  }

  if (recipe.time || recipe.servings) {
    const meta = document.createElement('div');
    meta.className = 'recipe-meta';
    if (recipe.time) meta.innerHTML += `<span>⏱ ${esc(recipe.time)}</span>`;
    if (recipe.servings) meta.innerHTML += `<span>👥 ${esc(recipe.servings)}</span>`;
    recipeContent.appendChild(meta);
  }

  if (recipe.notes) {
    const notes = document.createElement('div');
    notes.style.cssText = 'font-size:13px;color:var(--muted);margin-bottom:8px;line-height:1.5';
    notes.textContent = recipe.notes;
    recipeContent.appendChild(notes);
  }

  if (recipe.ingredients?.length) {
    const h = document.createElement('div');
    h.className = 'recipe-section-title';
    h.textContent = 'Malzemeler';
    recipeContent.appendChild(h);
    const ul = document.createElement('ul');
    ul.className = 'recipe-ingredients';
    recipe.ingredients.forEach(ing => {
      const li = document.createElement('li');
      li.textContent = ing;
      ul.appendChild(li);
    });
    recipeContent.appendChild(ul);
  }

  if (recipe.steps?.length) {
    const h = document.createElement('div');
    h.className = 'recipe-section-title';
    h.textContent = 'Yapılışı';
    recipeContent.appendChild(h);
    const ol = document.createElement('ol');
    ol.className = 'recipe-steps';
    recipe.steps.forEach(step => {
      const li = document.createElement('li');
      li.textContent = step;
      ol.appendChild(li);
    });
    recipeContent.appendChild(ol);
  }

  const favBtn = document.createElement('button');
  favBtn.className = 'recipe-add-btn' + (isFav ? ' added' : '');
  favBtn.textContent = isFav ? '✅ Favorilere Eklendi' : '⭐ Favorilere Ekle';
  if (!isFav) {
    favBtn.addEventListener('click', async () => {
      await addFavorite(name);
      favBtn.classList.add('added');
      favBtn.textContent = '✅ Favorilere Eklendi';
    });
  }
  recipeContent.appendChild(favBtn);
}

// ── MY RECIPES ─────────────────────────────────────────────────────────────
const recipeForm = document.getElementById('recipe-form');
const myRecipesList = document.getElementById('myrecipes-list');
const myRecipesEmpty = document.getElementById('myrecipes-empty');

function clearRecipeForm() {
  document.getElementById('recipe-edit-id').value = '';
  document.getElementById('recipe-name').value = '';
  document.getElementById('recipe-time').value = '';
  document.getElementById('recipe-servings').value = '';
  document.getElementById('recipe-ingredients').value = '';
  document.getElementById('recipe-steps').value = '';
  document.getElementById('recipe-notes').value = '';
  document.getElementById('save-recipe-btn').textContent = 'Kaydet';
}

function showRecipeForm(recipe) {
  recipeForm.classList.remove('hidden');
  if (recipe) {
    document.getElementById('recipe-edit-id').value = recipe.id;
    document.getElementById('recipe-name').value = recipe.name;
    document.getElementById('recipe-time').value = recipe.time || '';
    document.getElementById('recipe-servings').value = recipe.servings || '';
    document.getElementById('recipe-ingredients').value = (recipe.ingredients || []).join('\n');
    document.getElementById('recipe-steps').value = (recipe.steps || []).join('\n');
    document.getElementById('recipe-notes').value = recipe.notes || '';
    document.getElementById('save-recipe-btn').textContent = 'Güncelle';
  } else {
    clearRecipeForm();
  }
  document.getElementById('recipe-name').focus();
}

function hideRecipeForm() {
  recipeForm.classList.add('hidden');
  clearRecipeForm();
}

function renderMyRecipes() {
  const badge = document.getElementById('myrecipes-badge');
  const n = S.myRecipes.length;
  if (badge) badge.textContent = n > 0 ? ` (${n})` : '';
  myRecipesList.innerHTML = '';
  myRecipesEmpty.style.display = n === 0 ? 'block' : 'none';
  myRecipesList.style.display = n === 0 ? 'none' : 'flex';

  S.myRecipes.forEach(item => {
    const row = document.createElement('div');
    row.className = 'myrecipe-item';
    const meta = [
      item.ingredient_count ? `${item.ingredient_count} malzeme` : null,
      item.step_count ? `${item.step_count} adım` : null,
      item.time || null,
    ].filter(Boolean).join(' · ');

    row.innerHTML = `
      <div class="myrecipe-item-main">
        <div class="myrecipe-name">${esc(item.name)}</div>
        <div class="myrecipe-meta">${esc(meta || 'Tarif detayı')}</div>
      </div>
      <div class="myrecipe-actions">
        <button class="edit-btn" title="Düzenle">✏️</button>
        <button class="del-btn" title="Sil">🗑</button>
      </div>
    `;

    row.querySelector('.myrecipe-item-main').addEventListener('click', () => openCustomRecipe(item.id));
    row.querySelector('.edit-btn').addEventListener('click', async e => {
      e.stopPropagation();
      const res = await api(`/my-recipes/${item.id}`);
      showRecipeForm(res.recipe);
      document.querySelector('.tab[data-tab="myrecipes"]').click();
    });
    row.querySelector('.del-btn').addEventListener('click', async e => {
      e.stopPropagation();
      if (!confirm(`"${item.name}" tarifini silmek istediğinden emin misin?`)) return;
      const res = await api('/my-recipes/delete', { id: item.id });
      S.myRecipes = res.recipes;
      renderMyRecipes();
      toast('🗑 Tarif silindi');
    });
    myRecipesList.appendChild(row);
  });
}

document.getElementById('toggle-recipe-form').addEventListener('click', () => {
  if (recipeForm.classList.contains('hidden')) {
    showRecipeForm(null);
  } else {
    hideRecipeForm();
  }
});

document.getElementById('cancel-recipe-btn').addEventListener('click', hideRecipeForm);

document.getElementById('save-recipe-btn').addEventListener('click', async () => {
  const name = document.getElementById('recipe-name').value.trim();
  if (!name) { toast('Yemek adı gerekli'); return; }
  const payload = {
    name,
    ingredients: document.getElementById('recipe-ingredients').value,
    steps: document.getElementById('recipe-steps').value,
    time: document.getElementById('recipe-time').value,
    servings: document.getElementById('recipe-servings').value,
    notes: document.getElementById('recipe-notes').value,
  };
  const editId = document.getElementById('recipe-edit-id').value;
  try {
    const res = editId
      ? await api('/my-recipes/update', { ...payload, id: parseInt(editId, 10) })
      : await api('/my-recipes/add', payload);
    S.myRecipes = res.recipes;
    renderMyRecipes();
    hideRecipeForm();
    toast(editId ? '✅ Tarif güncellendi' : '✅ Tarif kaydedildi');
  } catch(e) {
    toast('⚠️ ' + (e.message || 'Kaydedilemedi'));
  }
});

// ── SETTINGS ───────────────────────────────────────────────────────────────
function renderSettingsForm() {
  const p = S.preferences;
  document.getElementById('pref-person-count').value = p.person_count || '3';
  document.getElementById('pref-meal-type').value = p.meal_type || '';
  document.getElementById('pref-style').value = p.style || '';
  document.getElementById('pref-preferences').value = p.preferences || '';
  document.getElementById('pref-dislikes').value = p.dislikes || '';
}

document.getElementById('save-prefs-btn').addEventListener('click', async () => {
  const prefs = {
    person_count: document.getElementById('pref-person-count').value,
    meal_type: document.getElementById('pref-meal-type').value,
    style: document.getElementById('pref-style').value,
    preferences: document.getElementById('pref-preferences').value,
    dislikes: document.getElementById('pref-dislikes').value,
  };
  const res = await api('/preferences', prefs);
  S.preferences = res.preferences;
  toast('✅ Tercihler kaydedildi');
  document.getElementById('settings-drawer').classList.remove('open');
});

// Settings Drawer Toggles
const settingsDrawer = document.getElementById('settings-drawer');
document.getElementById('header-settings-btn').addEventListener('click', () => {
  settingsDrawer.classList.add('open');
});
document.getElementById('settings-close').addEventListener('click', () => {
  settingsDrawer.classList.remove('open');
});
document.getElementById('settings-overlay').addEventListener('click', () => {
  settingsDrawer.classList.remove('open');
});


// ── HOME FEED ──────────────────────────────────────────────────────────────
window.openRecipe = openRecipeByName;
window.addFav = addFavorite;

window.toggleChef = async function(name, btn) {
  if (S.chefSpecials.includes(name)) {
    await removeChefSpecial(name);
    btn.classList.remove('added');
    btn.textContent = '👨‍🍳';
  } else {
    await addChefSpecial(name);
    btn.classList.add('added');
    btn.textContent = '👑';
  }
};

window.toggleFav = async function(name, btn) {
  if (S.favorites.includes(name)) {
    await removeFavorite(name);
    btn.classList.remove('added');
    btn.textContent = '⭐';
  } else {
    await addFavorite(name);
    btn.classList.add('added');
    btn.textContent = '✅';
  }
};

async function loadHomeFeed() {
  const featCont = document.getElementById('home-featured-container');
  const altCont = document.getElementById('home-alternatives-container');
  
  featCont.innerHTML = '<div style="text-align:center; padding: 40px; color: var(--muted);">Yükleniyor...</div>';
  altCont.innerHTML = '';

  try {
    const res = await api('/api/home-feed');
    if (!res) throw new Error("Veri boş döndü");

    const f = res.featured;
    if (f) {
      const badge = f.source === 'plan' ? '<span style="background: var(--accent); padding: 2px 8px; border-radius: 12px; font-size: 10px; margin-left: 10px;">Planda</span>' : '';
      const isFav = S.favorites.includes(f.name);
      const isChef = S.chefSpecials.includes(f.name);
      // Use Bing image search for food pictures
      const imgUrl = "https://tse1.mm.bing.net/th?q=" + encodeURIComponent(f.name) + "+yemek&w=800&h=600&c=7";
      
      featCont.innerHTML = `
        <div class="featured-card">
          <img src="${imgUrl}" class="featured-img" onerror="this.src='https://images.unsplash.com/photo-1498837167922-ddd27525d352?w=800'" alt="${f.name}">
          <div class="featured-content">
            <div class="featured-title">${f.name} ${badge}</div>
            <div class="featured-desc">${f.description}</div>
            <div class="featured-meta">
              <span>⏱️ ${f.time}</span>
              <span>💪 ${f.difficulty}</span>
            </div>
            <div class="featured-btn-row">
              <button class="featured-btn" onclick="openRecipe('${f.name}')">Tarife Git</button>
              <button class="icon-btn fav-toggle-btn ${isFav ? 'added' : ''}" style="background:rgba(255,255,255,0.2); border:none; color:white;" onclick="event.stopPropagation(); toggleFav('${f.name}', this)">${isFav ? '✅' : '⭐'}</button>
              <button class="icon-btn chef-toggle-btn ${isChef ? 'added' : ''}" style="background:rgba(255,255,255,0.2); border:none; color:white;" onclick="event.stopPropagation(); toggleChef('${f.name}', this)">${isChef ? '👑' : '👨‍🍳'}</button>
            </div>
          </div>
        </div>
      `;
    }

    if (res.alternatives && res.alternatives.length > 0) {
      const listHtml = res.alternatives.map(a => {
        const img = "https://tse1.mm.bing.net/th?q=" + encodeURIComponent(a.name) + "+yemek&w=150&h=150&c=7";
        const isFav = S.favorites.includes(a.name);
        const isChef = S.chefSpecials.includes(a.name);
        return `
        <div class="alt-card" onclick="openRecipe('${a.name}')">
          <img src="${img}" class="alt-img" onerror="this.src='https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=150'">
          <div class="alt-info">
            <div class="alt-title">${a.name}</div>
            <div class="alt-desc">${a.description}</div>
            <div class="alt-meta"><span>⏱️ ${a.time}</span><span>💪 ${a.difficulty}</span></div>
          </div>
          <button class="icon-btn fav-toggle-btn ${isFav ? 'added' : ''}" style="width:32px;height:32px;background:none;border:none;margin:auto 0;" onclick="event.stopPropagation(); toggleFav('${a.name}', this)">${isFav ? '✅' : '⭐'}</button>
          <button class="icon-btn chef-toggle-btn ${isChef ? 'added' : ''}" style="width:32px;height:32px;background:none;border:none;margin:auto 0;" onclick="event.stopPropagation(); toggleChef('${a.name}', this)">${isChef ? '👑' : '👨‍🍳'}</button>
        </div>
        `;
      }).join('');
      altCont.innerHTML = `<div class="alt-list">${listHtml}</div>`;
    }
  } catch (err) {
    console.error("Home feed load failed:", err);
    featCont.innerHTML = `
      <div class="featured-card" style="padding: 24px; text-align: center; background: rgba(239, 68, 68, 0.08); border-color: rgba(239, 68, 68, 0.15);">
        <div style="font-size: 32px; margin-bottom: 12px;">⚠️</div>
        <div style="font-size: 15px; font-weight: 700; margin-bottom: 8px;">Bağlantı Sorunu</div>
        <div style="font-size: 13px; color: var(--muted); margin-bottom: 16px; line-height: 1.5;">
          Öneriler yüklenirken bir sorun oluştu. API sınırına ulaşıldı veya sunucu yanıt vermiyor olabilir.
        </div>
        <button class="featured-btn" onclick="loadHomeFeed()" style="max-width: 160px; margin: 0 auto; display: block;">Tekrar Dene</button>
      </div>
    `;
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
    send();
  }
});

// ── INIT ───────────────────────────────────────────────────────────────────


if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js?v=4').then(reg => reg.update()).catch(() => {});
}

async function loadInitialData() {
  initTheme();
  const tasks = [
    api('/favorites').then(r => { S.favorites = r.favorites; renderFavorites(); }),
    api('/chef-specials').then(r => { S.chefSpecials = r.chef_specials; renderChefSpecials(); }),
    api('/plan').then(r => { S.plan = r.plan; S.days = r.days; renderWeekGrid(); }),
    api('/preferences').then(r => { S.preferences = r.preferences; renderSettingsForm(); }),
    api('/my-recipes').then(r => { S.myRecipes = r.recipes; renderMyRecipes(); }),
  ];
  await Promise.allSettled(tasks);
  renderMyRecipes();
  loadHomeFeed();
}

loadInitialData();
