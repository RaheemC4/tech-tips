'use strict';

const panelAnimations = new WeakMap();
function animatePanel(element, opening, onClosed = () => {}, fadeOnly = false) {
  const previous = panelAnimations.get(element);
  const current = getComputedStyle(element);
  const start = previous ? {opacity: current.opacity, transform: current.transform} :
    {opacity: opening ? 0 : 1, transform: opening && !fadeOnly ? 'translateY(-10px) scale(.975)' : 'none'};
  previous?.cancel();
  if (matchMedia('(prefers-reduced-motion: reduce)').matches || !element.animate) {
    panelAnimations.delete(element);
    if (!opening) onClosed();
    return;
  }
  const end = {opacity: opening ? 1 : 0,
    transform: opening || fadeOnly ? 'none' : 'translateY(-6px) scale(.98)'};
  const animation = element.animate([start, end], {
    duration: opening ? 320 : 180, easing: opening ? 'cubic-bezier(.2,.8,.2,1)' : 'cubic-bezier(.4,0,.8,.4)', fill: 'both'
  });
  panelAnimations.set(element, animation);
  animation.finished.then(() => {
    if (panelAnimations.get(element) !== animation) return;
    if (!opening) onClosed();
    animation.cancel();
    panelAnimations.delete(element);
  }).catch(() => {});
}
function setThemeVisible(pop, btn, open) {
  if (!open && (pop.inert || !pop.classList.contains('show'))) return;
  pop.inert = !open;
  btn.classList.toggle('open', open);
  btn.setAttribute('aria-expanded', String(open));
  if (open) pop.classList.add('show');
  animatePanel(pop, open, () => pop.classList.remove('show'));
}

/* ---------- theme switcher ---------- */
const THEMES = [
  ['blue','#2f7dff','#34c6ff'], ['blurple','#5865f2','#8b5cf6'],
  ['purple','#8b5cf6','#c05cff'], ['red','#ff2d6b','#ff6a4d'],
  ['green','#16c98a','#38e0b0'], ['cyan','#12b6cf','#37d6e8'],
];
function currentTheme() {
  try { return localStorage.getItem('tl-theme') || 'blue'; } catch (e) { return 'blue'; }
}
function applyTheme(name) {
  if (!THEMES.some(t => t[0] === name)) name = 'blue';
  document.documentElement.setAttribute('data-theme', name);
  try { localStorage.setItem('tl-theme', name); } catch (e) {}
  if (window.pywebview?.api?.companion_theme) window.pywebview.api.companion_theme(name).catch(() => {});
  const pop = document.getElementById('themepop');
  if (pop) pop.querySelectorAll('.tsw').forEach(sw =>
    { sw.classList.toggle('active', sw.dataset.theme === name);
      sw.setAttribute('aria-pressed', String(sw.dataset.theme === name)); });
  // WebView2 does not resolve CSS vars inside SVG gradient stops, so set the
  // score-ring stop colours directly from the resolved accent values.
  requestAnimationFrame(() => {
    const cs = getComputedStyle(document.documentElement);
    const a = cs.getPropertyValue('--accent').trim();
    const b = cs.getPropertyValue('--accent-2').trim();
    const stops = document.querySelectorAll('#rg stop');
    if (stops[0]) { stops[0].setAttribute('stop-color', a); stops[0].style.stopColor = a; }
    if (stops[1]) { stops[1].setAttribute('stop-color', b); stops[1].style.stopColor = b; }
  });
}
function wireTheme() {
  applyTheme(currentTheme());
  const btn = document.getElementById('themebtn');
  if (!btn) return;
  let pop = document.getElementById('themepop');
  if (!pop) {
    pop = document.createElement('div');
    pop.id = 'themepop';
    pop.setAttribute('role','group'); pop.setAttribute('aria-label','Choose theme');
    pop.innerHTML = THEMES.map(t =>
      `<button type="button" class="tsw" data-theme="${t[0]}" title="${t[0]}" aria-label="${t[0]} theme"
        style="background:linear-gradient(135deg,${t[1]},${t[2]})"></button>`).join('');
    document.body.appendChild(pop);
    watchShellOverlay(pop);
    pop.querySelectorAll('.tsw').forEach(sw =>
      sw.onclick = () => { applyTheme(sw.dataset.theme); setThemeVisible(pop, btn, false); btn.focus(); });
  }
  const place = () => {
    // Hang it off the button itself so it stays put when the window resizes.
    const r = btn.getBoundingClientRect();
    pop.style.top = (r.bottom + 6) + 'px';
    pop.style.right = Math.max(8, window.innerWidth - r.right - 12) + 'px';
  };
  btn.setAttribute('aria-expanded','false');
  btn.setAttribute('aria-controls','themepop');
  pop.onkeydown = e => {
    if (e.key === 'Escape') { e.preventDefault(); setThemeVisible(pop, btn, false); btn.focus(); }
  };
  pop.onfocusout = () => queueMicrotask(() => {
    if (!pop.contains(document.activeElement) && document.activeElement !== btn) {
      setThemeVisible(pop, btn, false);
    }
  });
  btn.onclick = e => {
    e.stopPropagation();
    const open = btn.getAttribute('aria-expanded') !== 'true';
    setThemeVisible(pop, btn, open);
    if (open) { place(); (pop.querySelector('.active') || pop.querySelector('.tsw'))?.focus(); }
    applyTheme(currentTheme());
  };
  window.addEventListener('resize', () => { if (pop.classList.contains('show')) place(); });
  document.addEventListener('click', e => {
    // e.target is the SVG path when the icon itself is clicked, so match the
    // button by closest() rather than identity.
    if (pop.classList.contains('show') && !pop.contains(e.target) &&
        !(e.target.closest && e.target.closest('#themebtn'))) {
      setThemeVisible(pop, btn, false);
    }
  });
}
// apply the saved theme immediately (before boot) so there is no flash
applyTheme(currentTheme());


/* ---------- bridge to Python (falls back to demo data in a browser) ---- */
// Demo data is a DEVELOPMENT-ONLY preview aid. It must never stand in for
// real system state - doing so once showed one machine's specs on another's
// screen and made toggles look like they applied when nothing was written.
// It is now opt-in via ?demo=1 and can never trigger by accident.
const DEMO_ALLOWED = location.search.indexOf('demo=1') !== -1;
const IN_APP = location.protocol !== 'http:' && location.protocol !== 'https:';
let USE_DEMO = false;

function bridgeReady() {
  return typeof window.pywebview !== 'undefined' &&
         window.pywebview.api &&
         typeof window.pywebview.api.init === 'function';
}

// pywebview injects window.pywebview.api asynchronously, and the
// 'pywebviewready' event can fire a beat BEFORE the methods are attached.
// So poll for the real thing instead of trusting either signal alone.
let _bridgeWait = null;
function waitForBridge(ms) {
  if (bridgeReady()) return Promise.resolve(true);
  if (_bridgeWait) return _bridgeWait;
  _bridgeWait = new Promise(resolve => {
    const deadline = Date.now() + ms;
    let done = false;
    const finish = ok => {
      if (done) return;
      done = true; _bridgeWait = null; resolve(ok);
    };
    window.addEventListener('pywebviewready',
      () => { if (bridgeReady()) finish(true); }, { once: true });
    (function tick() {
      if (bridgeReady()) return finish(true);
      if (Date.now() > deadline) return finish(false);
      setTimeout(tick, 20);
    })();
  });
  return _bridgeWait;
}

let LAST_ERR = '';
async function api(name, ...args) {
  // A call can land while the bridge is still being injected. Wait it out.
  if (!bridgeReady() && !USE_DEMO) await waitForBridge(IN_APP ? 40000 : 1200);
  if (bridgeReady() && window.pywebview.api[name]) {
    try {
      const r = await window.pywebview.api[name](...args);
      if (r && r.__error__) { LAST_ERR = name + ': ' + r.__error__; banner(LAST_ERR); }
      return r;
    } catch (e) {
      LAST_ERR = name + ': ' + (e && e.message ? e.message : e);
      banner(LAST_ERR);
      return null;
    }
  }
  if (USE_DEMO && DEMO_ALLOWED) return demo(name, args);
  // Bridge genuinely not reachable yet. NEVER show a hard error on startup -
  // return null so the caller can keep waiting behind the spinner.
  return null;
}

function banner(msg) {
  let el = document.getElementById('errbar');
  if (!el) {
    el = document.createElement('div');
    el.id = 'errbar';
    el.style.cssText = 'position:fixed;left:0;right:0;bottom:0;z-index:200;' +
      'padding:11px 18px;font-size:12px;background:rgba(255,93,108,.16);' +
      'color:#ffb4bc;border-top:1px solid rgba(255,93,108,.35);' +
      'backdrop-filter:blur(14px);cursor:pointer;font-family:ui-monospace,Consolas,monospace';
    el.onclick = () => el.remove();
    document.body.appendChild(el);
  }
  el.textContent = msg + '   (click to dismiss)';
}

const ICONS = {
  close:'<path d="M6 6l12 12M18 6L6 18"/>',
  check:'<path d="M5 12l4 4L19 6"/>',
  chevron:'<path d="m6 9 6 6 6-6"/>',
  arrow:'<path d="M4 12h16m-6-6 6 6-6 6"/>',
  help:'<path d="M9 8a3 3 0 1 1 5 2.2c-1.2.8-2 1.3-2 3.3M12 18h.01"/>',
  home:'<path d="M3 10.5 12 3l9 7.5V21a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z"/>',
  bolt:'<path d="M13 2 4 14h6l-1 8 9-12h-6z"/>',
  gpu:'<rect x="2" y="6" width="20" height="12" rx="2"/><rect x="6" y="10" width="5" height="4" rx="1"/>',
  net:'<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a15 15 0 0 1 0 18a15 15 0 0 1 0-18"/>',
  cpu:'<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/>',
  shield:'<path d="M12 2 20 6v6c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V6z"/>',
  nvidia:'<path d="M9 8c-2.6.3-4.4 2-4.9 3.9 1.2 2.3 3.6 3.6 6.4 3.4 3.4-.2 6-2.2 7.5-5-2-2.9-5.2-4.6-9-3.3zm2 1.9c2 0 3.6 1.4 3.6 3.1 0 1.8-1.6 3.2-3.6 3.2-.5 0-1-.1-1.4-.3 1.1-.1 1.9-.9 1.9-1.9 0-1.1-1-2-2.2-2-.3 0-.6 0-.8.1.6-1.3 1.9-2.2 3.5-2.2z"/>',
  folder:'<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
  disk:'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 8h.01"/>',
  wrench:'<path d="M15 3a6 6 0 0 0-5.5 8.4L3 18v3h3l6.6-6.5A6 6 0 1 0 15 3"/>',
  driver:'<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M7 19v2h10v-2"/>',
  restore:'<path d="M3 12a9 9 0 1 0 3-6.7M3 4v5h5"/>',
  box:'<path d="M21 8v8a2 2 0 0 1-1 1.7l-7 4a2 2 0 0 1-2 0l-7-4A2 2 0 0 1 3 16V8a2 2 0 0 1 1-1.7l7-4a2 2 0 0 1 2 0l7 4A2 2 0 0 1 21 8"/><path d="M3.3 7 12 12l8.7-5M12 22V12"/>'
};
const svg = k => `<svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor"
  stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${ICONS[k]||ICONS.cpu}</svg>`;

let STATE = { tweaks: [], cats: [], page: 'Home', specs: {}, admin: true };

/* ---------- nav ---------- */
const NAV = [
  ['sec','GENERAL'], ['page','Home','home'],
  ['sec','TWEAKS'],
  ['cat','Performance','bolt'], ['cat','Graphics','gpu'], ['cat','GPU','gpu'],
  ['cat','Networking','net'], ['cat','Power','bolt'], ['cat','Advanced','cpu'],
  ['cat','System','wrench'], ['cat','Privacy','shield'], ['cat','Explorer & UI','folder'],
  ['sec','SYSTEM'],
  ['page','System Info','info'], ['page','Disk Cleanup','disk'],
  ['page','Drivers','driver'], ['page','NVIDIA Profile','nvidia'], ['page','Defender','shield'], ['page','Resources','wrench'],
  ['sec','TOOLS'],
  ['page','Extra Tools','box'],
  ['page','Debloat & Customization','wrench'],
  ['page','Virtual Machines','box'],
  ['page','Install Apps','box'],
  ['page','Boot Optimizer','bolt'], ['page','BIOS Info','cpu'],
  ['page','System Restore','restore']
];

function buildNav() {
  const el = document.getElementById('navlist');
  let markup = '', group = null;
  for (const n of NAV) {
    if (n[0] === 'sec') {
      if (group) markup += '</div></section>';
      group = n[1];
      if (group === 'GENERAL') {
        markup += `<section class="navgroup" data-navgroup="GENERAL"><div class="navsec">GENERAL</div><div id="nav-GENERAL" class="navitems">`;
        continue;
      }
      markup += `<section class="navgroup" data-navgroup="${group}"><button type="button" class="navsec" aria-expanded="false" aria-controls="nav-${group}" data-navgroup-toggle="${group}">${group}<span aria-hidden="true">${svg('chevron')}</span></button><div id="nav-${group}" class="navitems" hidden>`;
      continue;
    }
    const chip = n[0] === 'cat' ? `<span class="chip" data-chip="${n[1]}">0/0</span>` : '';
    markup += `<button type="button" class="nav" data-nav="${n[1]}">${svg(n[2])}<span>${n[1]}</span>${chip}</button>`;
  }
  el.innerHTML = markup + '</div></section>';
  el.querySelectorAll('[data-nav]').forEach(n => n.onclick = () => show(n.dataset.nav));
  el.querySelectorAll('[data-navgroup-toggle]').forEach(button => button.onclick = () => {
    const open = button.getAttribute('aria-expanded') !== 'true';
    setNavGroup(button.dataset.navgroupToggle, open);
  });
  revealNav(STATE.page);
}

const navAnimations = new WeakMap();
function setNavGroup(name, open) {
  document.querySelectorAll('[data-navgroup]').forEach(group => {
    if (group.dataset.navgroup === 'GENERAL') return;
    const expanded = group.dataset.navgroup === name ? open : false;
    const heading = group.querySelector('.navsec');
    const items = group.querySelector('.navitems');
    // CSS height excludes the window's launch scale, preserving interruption position.
    const height = items.hidden ? 0 : parseFloat(getComputedStyle(items).height);
    const opacity = items.hidden ? 0 : Number(getComputedStyle(items).opacity);
    navAnimations.get(items)?.cancel();
    navAnimations.delete(items);
    heading.setAttribute('aria-expanded', String(expanded));
    items.inert = !expanded;
    items.setAttribute('aria-hidden', String(!expanded));
    if (!expanded && items.contains(document.activeElement)) heading.focus();
    items.hidden = false;
    items.style.overflow = 'hidden';
    const targetHeight = expanded ? items.scrollHeight : 0;
    if (matchMedia('(prefers-reduced-motion: reduce)').matches || height === targetHeight) {
      items.hidden = !expanded;
      items.style.overflow = '';
      return;
    }
    const animation = items.animate([
      {height: `${height}px`, opacity},
      {height: `${targetHeight}px`, opacity: expanded ? 1 : 0}
    ], {duration: 260, easing: 'cubic-bezier(.22,1,.36,1)', fill: 'both'});
    navAnimations.set(items, animation);
    animation.finished.then(() => {
      if (navAnimations.get(items) !== animation) return;
      items.hidden = !expanded;
      items.style.overflow = '';
      animation.cancel();
      navAnimations.delete(items);
    }).catch(() => {});
  });
}

function revealNav(name) {
  const button = document.querySelector(`[data-nav="${CSS.escape(name)}"]`);
  if (button) setNavGroup(button.closest('[data-navgroup]').dataset.navgroup, true);
}

let pageHistoryStarted = false;
function navigateHistory(direction) {
  if (!H('modal')?.classList.contains('show')) history.go(direction);
}
window.addEventListener('popstate', e => { if (e.state?.tlPage) show(e.state.tlPage, false); });
document.addEventListener('mouseup', e => {
  if (e.button === 3 || e.button === 4) { e.preventDefault(); navigateHistory(e.button === 3 ? -1 : 1); }
});
for (const type of ['mousedown','auxclick']) document.addEventListener(type, e => {
  if (e.button === 3 || e.button === 4) e.preventDefault();
});
document.addEventListener('keydown', e => {
  if (e.altKey && ['ArrowLeft','ArrowRight'].includes(e.key)) {
    e.preventDefault(); navigateHistory(e.key === 'ArrowLeft' ? -1 : 1);
  }
});
function show(name, recordHistory = true) {
  if (recordHistory) {
    if (!pageHistoryStarted) { history.replaceState({tlPage:name}, ''); pageHistoryStarted = true; }
    else if (history.state?.tlPage !== name) history.pushState({tlPage:name}, '');
  }
  if (typeof closeUpdates === 'function') closeUpdates();
  STATE.page = name;
  revealNav(name);
  document.querySelectorAll('[data-nav]').forEach(n => {
    const active = n.dataset.nav === name;
    n.classList.toggle('active', active);
    if (active) n.setAttribute('aria-current', 'page');
    else n.removeAttribute('aria-current');
  });
  const isCat = STATE.cats.includes(name);
  const routes = {
    'Extra Tools': pageUpdates,
    'Debloat & Customization': pageDebloat,
    'System Info': pageSysInfo, 'Disk Cleanup': pageClean,
    'Drivers': pageDrivers, 'NVIDIA Profile': pageNvProfile, 'Defender': pageDefender, 'Resources': pageRes,
    'Install Apps': pageApps, 'Virtual Machines': pageVirt,
    'Boot Optimizer': pageBoot, 'BIOS Info': pageBios,
    'System Restore': pageRestore, 'Networking': pageNetworking,
  };
  if (routes[name]) { routes[name](); return; }
  document.querySelectorAll('.page').forEach(p => p.classList.remove('show'));

  if (isCat) {
    document.getElementById('crumb').textContent = 'Tweaks › ' + name;
    document.getElementById('ptitle').textContent = name;
    document.getElementById('psub').textContent = 'Toggle a tweak to apply it. Toggle off to revert.';
    renderTweaks(name);
    document.getElementById('page-tweaks').classList.add('show');
  } else {
    document.getElementById('crumb').textContent = 'General › ' + name;
    document.getElementById('ptitle').textContent = name === 'Home' ? 'Overview' : name;
    document.getElementById('psub').textContent = name === 'Home'
      ? 'How tuned this machine is right now.' : '';
    document.getElementById('page-home').classList.add('show');
    // Rebuild the score ring, the number and the by-category grid from the
    // live tweak state every time Home opens - otherwise toggling on a
    // category page leaves the dashboard showing stale counts.
    if (name === 'Home') refreshCounts();
  }
  document.getElementById('scroll').scrollTop = 0;
}


/* Toggle handling.

   The switch flips the instant you click it and the registry write happens
   behind it. Waiting for Python before moving the switch is what made rapid
   toggling feel like it was lagging. Writes for one tweak are chained so a
   fast on/off/on always ends in the state you last chose. */
const INFLIGHT = {};

function paintCard(t) {
  const card = document.querySelector(`.card.tweak[data-key="${CSS.escape(t.key)}"]`);
  if (!card) return;
  card.classList.toggle('on', !!t.applied);
  const sw = card.querySelector('.sw');
  if (sw) {
    sw.classList.toggle('on', !!t.applied);
    if (sw.getAttribute('role') === 'switch') sw.setAttribute('aria-checked', String(!!t.applied));
  }
  const badge = card.querySelector('.badge');
  if (badge) {
    badge.textContent = t.applied == null ? 'UNKNOWN' : t.applied ? 'APPLIED' : 'NOT APPLIED';
    badge.className = 'badge' + (t.applied ? ' on' : '');
  }
}

function setToggle(key) {
  if (BULK_BUSY) return;
  const t = STATE.tweaks.find(x => x.key === key);
  if (!t) return;
  const want = !t.applied;
  const intent = t._intent = (t._intent || 0) + 1;
  t.applied = want;
  paintCard(t); updateCounts();
  const run = async () => {
    let r;
    try { r = await api('toggle', key, want); }
    catch (e) { r = {ok:false, message:e.message}; }
    if (intent !== t._intent) return;
    t.applied = typeof r?.applied === 'boolean' ? r.applied : null;
    paintCard(t); updateCounts();
    if (!r?.ok) banner(t.name + ': ' + (r?.message || 'Could not verify the change. Rescan to check.'));
  };
  INFLIGHT[key] = (INFLIGHT[key] || Promise.resolve()).then(run, run);
}

function reconcileTweaks(result, affected = STATE.tweaks) {
  STATE.tweaks.forEach(t => {
    if (result?.applied && Object.hasOwn(result.applied, t.key)) t.applied = result.applied[t.key];
    else if (affected.includes(t)) t.applied = null;
    paintCard(t);
  });
  refreshCounts(); updateCounts();
}

async function applyCategory(category, on) {
  if (BULK_BUSY) return;
  if (on && !await confirmAction('Apply all in this category?', 'This applies every option in ' + category + ', including any marked warnings.', 'Apply All')) return;
  if (BULK_BUSY) return;
  BULK_BUSY = true;
  try {
    await Promise.all(Object.values(INFLIGHT));
    const result = await api('bulk', category, on);
    reconcileTweaks(result, STATE.tweaks.filter(t => t.category === category));
    if (!result?.ok) banner('Some changes could not be verified. ' + (result?.message || Object.values(result?.errors || {}).join(' ')));
  } catch (error) { reconcileTweaks(null, STATE.tweaks.filter(t => t.category === category)); banner('Could not finish: ' + error.message); }
  finally { BULK_BUSY = false; }
}

function updateCounts() {
  let total = 0, applied = 0;
  STATE.cats.forEach(c => {
    const items = STATE.tweaks.filter(t => t.category === c);
    const on = items.filter(t => t.applied).length;
    total += items.length; applied += on;
    const chip = document.querySelector(`[data-chip="${CSS.escape(c)}"]`);
    if (chip) { chip.textContent = `${on}/${items.length}`;
      chip.style.color = on ? 'var(--good)' : 'var(--faint)'; }
  });
  const cc = H('catCount');
  if (cc && STATE.cats.includes(STATE.page)) {
    const items = STATE.tweaks.filter(t => t.category === STATE.page);
    cc.textContent = `${items.filter(t => t.applied).length}/${items.length} applied`;
  }
  H('footCount').textContent = `${applied} tweak${applied === 1 ? '' : 's'} applied`;
  const pct = total ? applied / total * 100 : 0;
  const ring = H('ring');
  if (ring) ring.style.strokeDashoffset = 490 - 490 * pct / 100;
  // The score number lives on the dashboard; keep it matching the ring so a
  // toggle never leaves "90" frozen next to a moved ring.
  const sn = H('scoreNum');
  if (sn) sn.textContent = Math.round(pct);
}

/* ---------- tweak cards ---------- */
function renderTweaks(cat) {
  const items = STATE.tweaks.filter(t => t.category === cat);
  const on = items.filter(t => t.applied).length;
  document.getElementById('catCount').textContent = `${on}/${items.length} applied`;
  document.getElementById('tweakGrid').innerHTML = items.map(t => `
    <div class="card tweak ${t.applied ? 'on' : ''}" data-key="${t.key}">
      <div class="top">
        <div class="ico">${svg(t.icon || 'cpu')}</div>
        <h3>${t.name}</h3>
      </div>
      <div class="desc">${t.desc}</div>
      ${t.warning ? `<div class="warnpill">▲ ${t.warning}</div>` : ''}
      <div class="foot">
        <span class="badge ${t.applied ? 'on' : ''}">
          ${t.applied == null ? 'UNKNOWN' : t.applied ? 'APPLIED' : 'NOT APPLIED'}</span>
        <button type="button" class="sw ${t.applied ? 'on' : ''}" data-sw="${t.key}" role="switch" aria-checked="${t.applied === true}" aria-label="${t.name}"></button>
      </div>
    </div>`).join('');

  document.querySelectorAll('[data-sw]').forEach(sw => {
    sw.onclick = () => setToggle(sw.dataset.sw);
  });
  wireTips();
}

async function applyAll(on) {
  return applyCategory(STATE.page, on);
}

/* ---------- dashboard one-click setup ---------- */
// Tweaks "Apply recommended" leaves off - kept in sync with the server's
// RECOMMENDED_SKIP: the two risky ones plus GameDVR and Fullscreen Optimizations.
const RECOMMENDED_KEYS = ['bing_search','cdm_ads','telemetry','ceip','feedback','activity_history','ad_id','typing_insights','speech_data','ink_collection','pause_windows_updates'];

function wireBulk() {
  document.querySelectorAll('[data-bulk]').forEach(b => {
    b.onclick = () => runBulk(b.dataset.bulk);
  });
}

let BULK_BUSY = false;
async function runBulk(mode) {
  if (BULK_BUSY) return;
  if (mode === 'all' && !await confirmAction('Apply every tweak?', 'This includes the legacy gaming tweaks, NVIDIA profile, Defender changes, a Windows Update pause until 31 December 2051 and all curated Debloat & Customization options. Apps will be removed and Start pins cleared once. Use Recommended for the preset that preserves gaming and core Windows features.', 'Apply All')) return;
  BULK_BUSY = true;
  try {
  const btns = document.querySelectorAll('[data-bulk]');
  btns.forEach(b => b.disabled = true);
  const status = H('debloatStatus') || H('bulkStatus');

  await Promise.all(Object.values(INFLIGHT));

  const setStatus = (txt, spin) => {
    if (!status) return;
    status.hidden = false;
    status.replaceChildren();
    if (spin) { const icon = document.createElement('span'); icon.className = 'spin'; status.append(icon); }
    const label = document.createElement('span'); label.textContent = txt; status.append(label);
  };
  const LABEL = {all: 'Applying every tweak', recommended: 'Applying the recommended tweaks',
                 revert: 'Restoring this session’s tweak changes', defaults: 'Restoring Windows defaults'}[mode];
  setStatus(LABEL + '...', true);

  // 2) Write the tweaks.
  const r = await api('bulk_tweaks', mode, mode === 'all');
  reconcileTweaks(r);

  // 3) Defender + NVIDIA, per mode.
  const extras = [];
  let complete = r?.ok === true;
  if (!complete) extras.push(r?.message || 'Some tweaks failed or could not be verified. ' + Object.values(r?.errors || {}).join(' '));
  if (mode === 'all' || mode === 'recommended') {
    setStatus('Applying debloat and customization...', true);
    const started = await api('debloat_apply', mode, [], mode === 'all');
    const dr = started?.ok ? await waitForDebloat() : started;
    complete = complete && dr?.ok === true;
    extras.push(dr?.message || 'Debloat could not start. Check its tab.');
  }
  const wantDefenderOff = (mode === 'all');
  const wantDefenderOn  = (mode === 'defaults');
  const wantNvidiaOn    = (mode === 'all');
  const wantNvidiaOff   = (mode === 'defaults');

  // Only touch NVIDIA when this PC actually has an NVIDIA GPU + the tool.
  let nv = null;
  try { nv = await api('nvprofile_status'); } catch (e) {}
  const nvUsable = nv && nv.nvidia && nv.tool && nv.profile;
  if ((wantNvidiaOn || wantNvidiaOff) && (!nv || (nv.nvidia && !nvUsable))) {
    complete = false; extras.push('NVIDIA profile availability could not be confirmed.');
  }

  if (wantNvidiaOn && nvUsable) {
    setStatus(LABEL + ' — applying NVIDIA profile...', true);
    const nr = await api('nvprofile_set', true);
    complete = complete && nr?.ok === true;
    extras.push(nr?.ok === true ? 'NVIDIA profile applied'
                                      : 'NVIDIA profile could not apply');
  } else if (wantNvidiaOn && nv && !nv.nvidia) {
    extras.push('No NVIDIA GPU — profile skipped');
  } else if (wantNvidiaOff && nvUsable) {
    setStatus(LABEL + ' — restoring NVIDIA settings...', true);
    const nr = await api('nvprofile_set', false);
    complete = complete && nr?.ok === true;
    extras.push(nr?.ok === true ? 'NVIDIA settings restored' : 'NVIDIA settings could not be restored');
  }

  if (wantDefenderOff || wantDefenderOn) {
    setStatus(LABEL + ' — ' + (wantDefenderOff ? 'turning Defender off' : 'turning Defender on') + '...', true);
    const dr = await api('defender_set', wantDefenderOn);
    complete = complete && dr?.ok === true;
    if (dr && dr.tamper && wantDefenderOff)
      extras.push('Defender needs one manual step — open the Defender tab to finish');
    else
      extras.push(dr?.ok === true ? (wantDefenderOff ? 'Defender turned off' : 'Defender turned on') : 'Defender change could not be confirmed');
  }

  // Virtualisation: the apply modes and Windows Defaults are all gaming-facing,
  // so put the machine in the gaming/protected state. Revert All is left alone
  // because we did not record which mode the PC was in beforehand.
  if (mode === 'all' || mode === 'defaults') {
    try {
      const vs = await api('virt_status');
      if (!vs) { complete = false; extras.push('Virtualisation status could not be read.'); }
      if (vs && vs.mode !== 'gaming') {
        setStatus(LABEL + ' — setting up for gaming...', true);
        const vr = await api('virt_set', 'gaming');
        complete = complete && vr?.ok === true;
        if (vr && vr.ok) extras.push('Set up for gaming, Memory Integrity off (restart needed)');
      }
    } catch (e) { complete = false; extras.push('Virtualisation change failed: ' + e.message); }
  }

  const done = {all: 'Applied everything.', recommended: 'Recommended tweaks applied.',
                revert: 'Session tweak changes restored. Other tools and app removals are not included.', defaults: 'Windows defaults restored.'}[mode];
  setStatus((complete ? done : 'Finished with failures or unverified changes.') + (extras.length ? '  •  ' + extras.join('  •  ') : ''), false);

  } catch (error) {
    reconcileTweaks(null);
    const target = H('debloatStatus') || H('bulkStatus');
    if (target) { target.hidden = false; target.textContent = 'Could not finish: ' + error.message; }
  } finally {
    document.querySelectorAll('[data-bulk]').forEach(b => b.disabled = false);
    BULK_BUSY = false;
  }
}

async function rescan() {
  const res = await api('scan');
  if (res) { STATE.tweaks = res; renderTweaks(STATE.page); refreshCounts(); }
}

/* ---------- home ---------- */
function refreshCounts() {
  let total = 0, applied = 0;
  STATE.cats.forEach(c => {
    const items = STATE.tweaks.filter(t => t.category === c);
    const on = items.filter(t => t.applied).length;
    total += items.length; applied += on;
    const chip = document.querySelector(`[data-chip="${CSS.escape(c)}"]`);
    if (chip) { chip.textContent = `${on}/${items.length}`;
      chip.style.color = on ? 'var(--good)' : 'var(--faint)'; }
  });
  const pct = total ? applied / total * 100 : 0;
  document.getElementById('ring').style.strokeDashoffset = 490 - 490 * pct / 100;
  animateNum(document.getElementById('scoreNum'), pct);
  document.getElementById('scoreNote').textContent =
    pct >= 90 ? 'Just about everything is applied.' :
    pct >= 60 ? `Well tuned. ${total - applied} tweak(s) still available.` :
    pct >= 25 ? `Partly tuned - ${total - applied} tweak(s) not applied yet.` :
    'Mostly untouched. Make a restore point, then work through the categories.';
  document.getElementById('footCount').textContent =
    `${applied} tweak${applied === 1 ? '' : 's'} applied`;

  document.getElementById('catGrid').innerHTML = STATE.cats.map(c => {
    const items = STATE.tweaks.filter(t => t.category === c);
    const on = items.filter(t => t.applied).length;
    const p = items.length ? on / items.length * 100 : 0;
    return `<button type="button" class="card" onclick="show('${c.replace(/'/g, "\\'")}')" style="cursor:pointer;padding:15px">
      <div class="row"><span style="font-size:12.5px;font-weight:620">${c}</span>
      <div class="spacer"></div><span style="font-size:11px;color:${on ? 'var(--good)' : 'var(--faint)'}">${on}/${items.length}</span></div>
      <div class="bar"><i style="width:${p}%"></i></div></button>`;
  }).join('');
}

function animateNum(el, to) {
  if (document.body.classList.contains('booting') || matchMedia('(prefers-reduced-motion: reduce)').matches) {
    el.textContent = Math.round(to);
    return;
  }
  const from = parseFloat(el.textContent) || 0;
  const t0 = performance.now();
  (function step(now) {
    const k = Math.min(1, (now - t0) / 900);
    const e = 1 - Math.pow(1 - k, 3);
    el.textContent = Math.round(from + (to - from) * e);
    if (k < 1) requestAnimationFrame(step);
  })(t0);
}

function buildQuick() {
  const acts = [
                ['Run Boot Optimizer','Boot Optimizer'],
                ['Test Connection','Networking'],
                ['Clean Up Disk','Disk Cleanup'],
                ['Check Drivers','Drivers'],
                ['Create a restore point','System Restore']];
  document.getElementById('quickRow').innerHTML = acts.map(
    ([l, t]) => `<button class="btn ghost" onclick="${t === 'Networking' ? 'openConnectionTest()' : `show('${t}')`}">${l}</button>`).join('');
}
function openConnectionTest() {
  show('Networking');
  if (!NET_JOB.running && !NET_JOB.result) runNetTest();
}

function renderSpecs(s) {
  if (!s || typeof s !== 'object') return;
  STATE.specs = s;
  document.getElementById('specs').innerHTML = Object.entries(s).map(
    ([k, v]) => `<div class="specrow"><span class="k">${k}</span><span class="v">${v}</span></div>`).join('');
}

/* ---------- tooltips ---------- */
const tip = document.getElementById('tip');
tip.setAttribute('role','tooltip');
function wireTips() {
  document.querySelectorAll('.info[data-t]').forEach(el => {
    el.innerHTML = svg('help');
    el.onmouseenter = () => {
      const [t, b, g] = el.dataset.t.split('|');
      tip.innerHTML = `<b>${t}</b><p>${b}</p>${g ? `<div class="good">${g}</div>` : ''}`;
      const r = el.getBoundingClientRect();
      tip.classList.add('show');
      const tw = tip.offsetWidth, th = tip.offsetHeight;
      tip.style.left = Math.min(r.left, innerWidth - tw - 14) + 'px';
      tip.style.top = (r.bottom + th + 14 > innerHeight ? r.top - th - 10 : r.bottom + 10) + 'px';
    };
    el.tabIndex = 0;
    el.setAttribute('role','button');
    el.setAttribute('aria-label','About ' + el.dataset.t.split('|')[0]);
    el.setAttribute('aria-describedby','tip');
    el.onfocus = el.onmouseenter;
    el.onblur = () => tip.classList.remove('show');
    el.onkeydown = e => {
      if (e.key === 'Escape') { e.preventDefault(); tip.classList.remove('show'); }
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); el.onmouseenter(); }
    };
    el.onmouseleave = () => { if (document.activeElement !== el) tip.classList.remove('show'); };
  });
}

/* ---------- boot ---------- */
let boot = async function boot() {
  document.body.classList.add('booting');
  // Keep the spinner up and keep asking until the backend actually answers.
  // Never drop to an empty shell or an error - just stay patient.
  let info = await api('init');
  for (let i = 0; !info && i < 400; i++) {          // ~ up to 2 min of retries
    await new Promise(r => setTimeout(r, 300));
    info = await api('init');
  }
  if (info) {
    STATE.tweaks = info.tweaks; STATE.cats = info.categories;
    STATE.admin = info.admin;
    document.getElementById('footAdmin').textContent =
      info.admin ? 'Administrator' : 'Not elevated';
    document.getElementById('footAdmin').style.color =
      info.admin ? 'var(--good)' : 'var(--warn)';
    renderSpecs(Object.keys(STATE.specs).length ? STATE.specs : (info.specs || {}));
  }
  const sharedTheme = await api('companion_theme');
  if (THEMES.some(t => t[0] === sharedTheme)) {
    try { localStorage.setItem('tl-theme', sharedTheme); } catch (e) {}
  }
  buildNav(); show('Home'); refreshCounts(); wireTips(); wireTheme();
  buildQuick(); wireBulk();
  // Commit Home underneath the loader before beginning the handoff.
  await new Promise(resolve => setTimeout(resolve, 0));
  document.body.classList.add('launch-ready');
  document.body.classList.remove('booting', 'booting-slow');
  // The native host stays hidden until Home, rather than the centred loader,
  // is the first frame it can reveal. Browser previews retain the same entrance.
  await new Promise(resolve => setTimeout(resolve, 0));
  await api('reveal');
  if (typeof startUpdateMonitor === 'function') startUpdateMonitor();
  if (info?.open_updates && typeof openUpdates === 'function') openUpdates();
  if (info && info.scanning) {
    H('scoreNote').textContent = info.tweaks?.length ? 'Refreshing last checked results...' : 'Checking what is already applied...';
    if (!Object.keys(STATE.specs).length) renderSpecs({ Status: 'Reading hardware...' });
  } else {
    const later = await api('specs');
    if (later && typeof later === 'object') renderSpecs(later);
  }
}

;
/* ---------- demo data for browser preview ---------- */
function demo(name, args) {
  if (name === 'init') {
    const cats = ['Performance','Graphics','GPU','Networking','Power','Advanced','System','Privacy','Explorer & UI'];
    const mk = (c, n) => Array.from({length:n}, (_, i) => ({
      key: c + i, name: ['Disable GameDVR','Enable Game Mode','Hardware GPU Scheduling',
        'Disable Mouse Acceleration','Ultimate Performance Plan','Disable Nagle’s Algorithm',
        'Network Throttling Off','Disable Telemetry','Restore Classic Context Menu'][i % 9],
      desc: 'Turns off Xbox Game Bar background recording. One of the biggest free FPS wins on Windows 11.',
      category: c, applied: Math.random() > .5, locked: Math.random() > .85,
      icon: ['bolt','gpu','net','cpu','shield'][i % 5],
      warning: i === 3 ? 'Breaks Valorant, Vanguard and some anti-cheats' : null
    }));
    return { categories: cats, admin: true,
      tweaks: cats.flatMap(c => mk(c, 3 + (c.length % 5))),
      specs: { CPU:'Intel Core i9-14900K', Graphics:'NVIDIA GeForce RTX 5090',
        Memory:'32 GB @ 6000 MT/s', Motherboard:'MSI MPG Z690 EDGE WIFI',
        Windows:'Windows 11 Pro (build 26200)', Storage:'Samsung SSD 990 PRO 2TB' } };
  }
  return true;
}
async function startWhenReady() {
  if (bridgeReady()) { boot(); return; }

  // A browser preview will never get a bridge - bail quickly to demo data.
  if (!IN_APP) {
    const ok = await waitForBridge(1200);
    if (!ok && DEMO_ALLOWED) USE_DEMO = true;
    boot();
    return;
  }

  // Inside the real app the WebView2 bridge ALWAYS arrives - it can just be
  // slow on a freshly-extracted folder while Windows scans the files. So we
  // wait for it indefinitely behind a calm "Starting..." splash and NEVER show
  // an error for slowness. The only job here is to look patient, not broken.
  document.body.classList.add('booting');
  const t0 = Date.now();
  (function poll() {
    if (bridgeReady()) {
      boot();
      return;
    }
    // After a while, reassure rather than alarm - still no error.
    if (Date.now() - t0 > 20000) document.body.classList.add('booting-slow');
    setTimeout(poll, 40);
  })();
  window.addEventListener('pywebviewready', () => {
    if (bridgeReady() && !window.__booted) {
      boot();
    }
  }, { once: true });
}
const _origBoot = boot;
boot = async function () {
  if (window.__booted) return;
  window.__booted = true;
  return _origBoot();
};
startWhenReady();

/* =====================================================================
   Additional pages - system info, cleanup, drivers, tools, networking
   ===================================================================== */

window.py_scanned = d => {
  if (!d || !d.tweaks) return;
  const busy = new Set(Object.keys(INFLIGHT));
  const prev = new Map(STATE.tweaks.map(t => [t.key, t.applied]));
  const hadNone = STATE.tweaks.length === 0;
  STATE.tweaks = d.tweaks.map(t =>
    busy.has(t.key) ? { ...t, applied: prev.get(t.key) } : t);

  // init() now returns an empty list so it can answer instantly, so this is
  // where the real tweaks (and the categories that actually have any) land.
  if (d.categories && d.categories.length) {
    const changed = d.categories.join('|') !== STATE.cats.join('|');
    STATE.cats = d.categories;
    if (changed || hadNone) buildNav();
  }
  refreshCounts();
  if (hadNone) { buildQuick(); wireBulk(); }
  if (STATE.cats.includes(STATE.page)) renderTweaks(STATE.page);
  if (STATE.page === 'Home') show('Home');
  if (STATE.page === 'Networking') pageNetworking();
};
window.py_specs = d => renderSpecs(d);

/* ---------- long-running jobs (SFC, DISM, disk check, driver download) ------
   Jobs live on the Python side, so leaving a tab and coming back finds the
   job still running with its live progress instead of a fresh Run button.
   Every job pushes 'job' events; each page registers a renderer by job key. */
const JOBS = {};                 // key -> latest job snapshot
const JOB_RENDERERS = {};        // key -> fn(job)

window.py_job = job => {
  if (!job || !job.key) return;
  JOBS[job.key] = job;
  const r = JOB_RENDERERS[job.key];
  if (r) r(job);
};

async function restoreJobs() {
  // Called when a page mounts: pull whatever is still running so the page can
  // paint its in-progress state.
  let list = [];
  try { list = await api('active_jobs') || []; } catch (e) {}
  list.forEach(j => {
    JOBS[j.key] = j;
    const r = JOB_RENDERERS[j.key];
    if (r) r(j);
  });
}

// The NVIDIA settings are read once in the background at startup, so the tab
// opens instantly. If the user got there before the read finished, this fills
// it in the moment it lands.
window.py_nvready = () => {
  if (STATE.page !== 'NVIDIA Profile') return;
  refreshNvProfile();
  loadNvSettings();
};

window.onPy = (event, data) => {
  const h = window['py_' + event];
  if (h) h(data);
};

const H = (id) => document.getElementById(id);
function pageShell(title, sub, html) {
  H('crumb').textContent = sub.crumb;
  H('ptitle').textContent = title;
  H('psub').textContent = sub.text || '';
  const el = H('page-generic');
  el.innerHTML = html;
  document.querySelectorAll('.page').forEach(p => p.classList.remove('show'));
  el.classList.add('show');
  H('scroll').scrollTop = 0;
  wireTips();
}

/* ---------------- System Info ---------------- */
let SYS_SEC = 'CPU';
async function pageSysInfo() {
  const secs = await api('sysinfo_sections') || ['CPU'];
  pageShell('System Information', {crumb:'System › System Info',
    text:'What is actually inside this machine.'},
    `<div class="row" id="sysTabs" style="margin-bottom:16px"></div>
     <div class="row" style="margin-bottom:12px">
       <button class="btn ghost" onclick="refreshAll()">Re-read hardware</button>
       <span style="color:var(--faint);font-size:11.5px">Read once when the app
       opens - components rarely change while it is running.</span></div>
     <div class="grid g3" id="sysBody"><div class="card">Reading...</div></div>`);
  H('sysTabs').innerHTML = secs.map(sname =>
    `<button class="btn ghost" data-sec="${sname}">${sname}</button>`).join('');
  H('sysTabs').querySelectorAll('[data-sec]').forEach(b =>
    b.onclick = () => loadSys(b.dataset.sec));
  loadSys(secs.includes(SYS_SEC) ? SYS_SEC : secs[0]);
}
const SYSCACHE = {};
async function loadSys(name) {
  SYS_SEC = name;
  document.querySelectorAll('[data-sec]').forEach(b =>
    b.className = 'btn ' + (b.dataset.sec === name ? '' : 'ghost'));
  if (SYSCACHE[name]) { paintSys(SYSCACHE[name]); return; }
  H('sysBody').innerHTML = '<div class="card">Reading...</div>';
  const groups = await api('sysinfo_section', name) || [];
  SYSCACHE[name] = groups;
  paintSys(groups);
}
function paintSys(groups) {
  if (!H('sysBody')) return;
  H('sysBody').innerHTML = groups.length ? groups.map(rows => `<div class="card">${
    rows.map(([k, v]) => `<div style="padding:7px 0">
      <div class="label">${k}</div>
      <div style="font-weight:600;font-size:13px;margin-top:2px">${v}</div></div>`).join('')
  }</div>`).join('') : '<div class="card">Nothing reported.</div>';
}

async function refreshAll() {
  Object.keys(SYSCACHE).forEach(k => delete SYSCACHE[k]);
  BIOSCACHE = null;
  await api('refresh_all');
  if (STATE.page === 'System Info') loadSys(SYS_SEC);
  if (STATE.page === 'BIOS Info') pageBios();
}

/* ---------------- Disk Cleanup ---------------- */
let CLEAN = [];
const CLEAN_JOB = {running:false, message:'', log:[], failed:false};
async function pageClean() {
  pageShell('Disk Cleanup', {crumb:'System › Disk Cleanup',
    text:'Find and remove junk that is safe to delete.'},
    `<div class="card clean-summary">
       <div class="row clean-actions"><h3 id="cleanTotal">Scanning...</h3>
       <div class="spacer"></div>
       <button class="btn ghost" id="cleanRescan" onclick="pageClean()">Rescan</button>
       <button class="btn" id="cleanRun" onclick="runClean()">Clean Up</button></div>
       <p id="cleanStatus" role="status" aria-live="polite"></p>
       <div class="bar"><i id="diskBar"></i></div>
       <p id="diskLbl"></p>
     </div>
     <div class="card clean-list" id="cleanList"></div>
     <details id="cleanDetails" class="clean-details"><summary>Cleanup details</summary>
       <div id="cleanLog"></div></details>`);
  renderClean();
  paintCleanJob();
  if (CLEAN_JOB.running) return;
  const list = H('cleanList');
  const d = await api('clean_scan');
  if (!d || CLEAN_JOB.running || STATE.page !== 'Disk Cleanup' || H('cleanList') !== list) return;
  CLEAN = d.items;
  H('diskBar').style.width = (d.disk.used / d.disk.total * 100) + '%';
  H('diskLbl').textContent =
    `Drive C: ${d.disk.usedH} of ${d.disk.totalH} used · ${d.disk.freeH} free`;
  renderClean();
}
function renderClean() {
  H('cleanList').innerHTML = CLEAN.map((it, i) => `
    <label class="clean-row">
      <input type="checkbox" ${it.default && it.bytes ? 'checked' : ''}
        ${!it.bytes || CLEAN_JOB.running ? 'disabled' : ''} data-cl="${i}">
      <span class="clean-copy"><b>${it.name}</b><span>${it.desc}${it.files ? ' · ' + it.files.toLocaleString() + ' files' : ''}</span></span>
      <b class="clean-size ${it.bytes ? 'available' : ''}">${it.human}</b>
    </label>`).join('');
  document.querySelectorAll('[data-cl]').forEach(c => c.onchange = recalcClean);
  recalcClean();
}
function recalcClean() {
  let t = 0;
  document.querySelectorAll('[data-cl]').forEach(c => {
    if (c.checked) t += CLEAN[+c.dataset.cl].bytes; });
  H('cleanTotal').textContent = human(t) + ' can be freed';
  H('cleanRun').disabled = CLEAN_JOB.running || !t;
}
function human(n) {
  const u = ['B','KB','MB','GB','TB']; let i = 0;
  while (n >= 1024 && i < 4) { n /= 1024; i++; }
  return (i < 2 ? Math.round(n) : n.toFixed(1)) + ' ' + u[i];
}
function paintCleanJob() {
  if (STATE.page !== 'Disk Cleanup' || !H('cleanRun')) return;
  H('cleanRun').textContent = CLEAN_JOB.running ? 'Cleaning...' : 'Clean Up';
  H('cleanRun').setAttribute('aria-busy', String(CLEAN_JOB.running));
  H('cleanRescan').disabled = CLEAN_JOB.running;
  H('cleanStatus').textContent = CLEAN_JOB.message;
  H('cleanStatus').classList.toggle('working', CLEAN_JOB.running);
  H('cleanStatus').classList.toggle('failed', CLEAN_JOB.failed);
  H('cleanLog').textContent = CLEAN_JOB.log.join('\n');
  H('cleanDetails').hidden = !CLEAN_JOB.log.length;
  document.querySelectorAll('[data-cl]').forEach(c => {
    c.disabled = CLEAN_JOB.running || !CLEAN[+c.dataset.cl].bytes;
  });
  recalcClean();
}
window.py_cleanlog = d => {
  if (!CLEAN_JOB.running) return;
  const message = `${d.name}: freed ${d.freed}${d.skipped ? `, ${d.skipped} in use` : ''}`;
  CLEAN_JOB.log.push(message);
  CLEAN_JOB.message = 'Cleaning... ' + message;
  paintCleanJob();
};
async function runClean() {
  if (CLEAN_JOB.running) return;
  const sel = [];
  document.querySelectorAll('[data-cl]').forEach(c => {
    if (c.checked) sel.push(CLEAN[+c.dataset.cl].id); });
  if (!sel.length) return;
  Object.assign(CLEAN_JOB, {running:true, message:'Cleaning selected files. Files in use will be skipped.', log:[], failed:false});
  paintCleanJob();
  const r = await api('clean_run', sel);
  CLEAN_JOB.running = false;
  CLEAN_JOB.failed = !r?.ok;
  CLEAN_JOB.message = r?.ok
    ? `Freed ${r.freed}${r.skipped ? ` · ${r.skipped} file(s) in use or protected were skipped` : ''}`
    : r?.message || 'Cleanup could not finish. Try again.';
  paintCleanJob();
  // Refresh sizes only if this page is still open; never navigate the user back.
  if (STATE.page === 'Disk Cleanup') pageClean();
}

/* ---------------- Drivers ---------------- */
async function pageDrivers() {
  pageShell('Graphics Drivers', {crumb:'System › Drivers',
    text:'Checked live against the vendor every time you open this page.'},
    `<div class="row" style="margin-bottom:15px">
      <button class="btn" onclick="pageDrivers()">Check for Updates</button>
      <span id="drvStatus" style="color:var(--muted);font-size:12px"></span></div>
     <div id="drvList"><div class="card">Querying vendor...</div></div>
     <div class="card" style="margin-top:14px"><p style="color:var(--muted);font-size:11.5px;line-height:1.6">
     Downloads come straight from the vendor's own servers over HTTPS, and the app
     refuses any link that is not on an nvidia.com or amd.com host. It saves the
     installer to your Downloads folder and opens it there - it will not run an
     installer for you.</p></div>`);
  const d = await api('check_drivers');
  H('drvStatus').textContent = 'Checked at ' + new Date().toLocaleTimeString();
  if (!d || d.error || !d.gpus) {
    H('drvList').innerHTML = `<div class="card">Could not check: ${d && d.error || 'unknown'}</div>`;
    return;
  }
  H('drvList').innerHTML = d.gpus.map((g, i) => {
    // Verdict comes from Python, which compares version NUMBERS. Comparing
    // the strings here reported an update whenever they merely differed -
    // including when the installed driver was newer than the listed one.
    const st = g.status || (g.latest ? 'unknown' : 'unknown');
    const needsUpdate = st === 'update';
    const good = st === 'current' || st === 'ahead';
    const LABEL = { current: 'UP TO DATE', ahead: 'NEWER THAN VENDOR',
                    update: 'UPDATE AVAILABLE', unknown: 'NOT CHECKED' };
    return `<div class="card" style="margin-bottom:11px">
      <div class="row"><b style="font-size:15px">${g.name}</b>
      <div class="spacer"></div>
      <span class="badge ${good ? 'on' : ''}"
        style="${needsUpdate ? 'background:rgba(255,190,61,.14);color:var(--warn)' : ''}">
        ${LABEL[st] || 'NOT CHECKED'}</span></div>
      <div class="row" style="margin-top:14px;gap:34px">
        <div><div class="label">INSTALLED</div>
          <div style="font-size:19px;font-family:ui-monospace,Consolas,monospace">${g.installed}</div></div>
        ${g.latest ? `<div><div class="label">LATEST</div>
          <div style="font-size:19px;font-family:ui-monospace,Consolas,monospace;
            color:${needsUpdate ? 'var(--warn)' : 'var(--good)'}">${g.latest}</div></div>` : ''}
      </div>
      ${st === 'ahead' ? `<div style="margin-top:10px;font-size:12px;color:var(--muted)">
        Your driver is newer than the newest one NVIDIA lists for this card -
        usually a beta, a hotfix, or one that came via the NVIDIA app. Nothing
        to do.</div>` : ''}
      <div class="row" style="margin-top:15px">
        ${needsUpdate ? `<button class="btn" data-dl="${i}">Download Driver</button>` : ''}
        <button class="btn ghost" onclick="api('open_url','${g.page}')">Open vendor page</button>
        <span id="dlp${i}" style="color:var(--muted);font-size:11.5px"></span></div>
    </div>`;
  }).join('');
  document.querySelectorAll('[data-dl]').forEach(b => {
    const i = +b.dataset.dl;
    const g = d.gpus[i];
    const jobkey = 'driver:' + i;
    const row = b.parentElement;              // the button row
    // Give the row a progress bar + cancel button it can show while running.
    const bar = document.createElement('div');
    bar.className = 'jobbar'; bar.style.cssText = 'display:none;flex:1;max-width:220px';
    bar.innerHTML = '<i></i>';
    const cancel = document.createElement('button');
    cancel.className = 'btn ghost'; cancel.textContent = 'Cancel';
    cancel.style.display = 'none';
    row.appendChild(bar); row.appendChild(cancel);

    const paint = job => {
      const running = job && job.state === 'running';
      b.style.display = running ? 'none' : '';
      cancel.style.display = running ? '' : 'none';
      bar.style.display = running ? '' : 'none';
      if (running) {
        const p = (job.progress || 0) * 100;
        bar.classList.toggle('indet', !job.progress);
        bar.querySelector('i').style.width = p + '%';
        H('dlp' + i).textContent = job.line || 'Downloading...';
      } else if (job && job.result) {
        const r = job.result;
        H('dlp' + i).textContent = r.ok ? 'Saved to Downloads'
          : (r.cancelled ? 'Cancelled' : 'Failed: ' + (r.error || ''));
      }
    };
    JOB_RENDERERS[jobkey] = paint;
    if (JOBS[jobkey]) paint(JOBS[jobkey]);

    b.onclick = async () => {
      paint({state: 'running', progress: 0, line: 'Starting...'});
      await api('download_driver', g.url, g.vendor, i);
    };
    cancel.onclick = () => api('cancel_download', jobkey);
  });
  restoreJobs();
}

/* ---------------- Boot Optimizer ---------------- */
async function pageBoot() {
  pageShell('Boot Optimizer', {crumb:'Tools › Boot Optimizer',
    text:'Automatic startup and shutdown tuning for this machine.'},
    `<div class="card" style="margin-bottom:14px"><p style="color:var(--muted);font-size:12px;line-height:1.65">
      Detects your CPU and GPU, then applies the boot tweaks that suit them.
      Secure Boot, TPM and VBS are never touched, so kernel anti-cheat keeps
      working. Every change is written to a rollback file.</p></div>
     <div class="row" style="margin-bottom:14px">
       <button class="btn ghost" onclick="runBoot('preview')">Preview Changes</button>
       <button class="btn" onclick="runBoot('apply')">Apply</button>
       <button class="btn ghost" onclick="runBoot('undo')">Undo</button></div>
     <div class="card" id="bootLive" style="display:none;text-align:center;padding:26px">
       <div id="bootStep" style="font-size:17px;font-weight:620"></div>
       <div id="bootAct" style="margin-top:12px;font-family:ui-monospace,Consolas,monospace;
         font-size:12px;color:var(--muted);background:rgba(0,0,0,.28);padding:11px;
         border-radius:11px"></div>
       <div id="bootFeed" style="margin-top:14px;text-align:left;font-size:12px"></div></div>
     <div id="bootRes"></div>`);
}
let bootFeed = [];
window.py_bootline = d => {
  const live = H('bootLive'); if (!live) return;
  live.style.display = 'block';
  if (d.kind === 'step') { H('bootStep').textContent = d.text; return; }
  const txt = d.text + (d.detail ? ' → ' + d.detail : '');
  H('bootAct').textContent = '// ' + txt;
  const col = {ok:'var(--good)', plan:'#6ba4e0', warn:'var(--warn)',
               fail:'var(--bad)'}[d.kind] || 'var(--faint)';
  bootFeed.push(`<div style="color:${col};padding:2px 0">● ${txt}</div>`);
  bootFeed = bootFeed.slice(-5);
  H('bootFeed').innerHTML = bootFeed.join('');
};
async function runBoot(mode) {
  bootFeed = []; H('bootRes').innerHTML = '';
  H('bootLive').style.display = 'block';
  H('bootStep').textContent = mode === 'preview' ? 'Preview' :
    (mode === 'undo' ? 'Undo' : 'Applying');
  const r = await api('boot_optimizer', mode);
  H('bootLive').style.display = 'none';
  if (!r || r.error) { H('bootRes').innerHTML =
    `<div class="card">Failed: ${r && r.error}</div>`; return; }
  const grp = (title, rows, col) => `<div class="card" style="margin-bottom:11px">
    <div class="row"><b>${title}</b><span class="badge" style="margin-left:9px">${rows.length}</span></div>
    ${rows.length ? rows.map(([t, dt]) => `<div style="padding:4px 0;font-size:12.5px">
      <span style="color:${col}">●</span> ${t}${dt ? ` <b style="color:var(--good)">→ ${dt}</b>` : ''}</div>`).join('')
      : `<p style="color:var(--faint);font-size:12px;margin-top:6px">Nothing here.</p>`}</div>`;
  H('bootRes').innerHTML = mode === 'preview'
    ? grp('Would change', r.planned, 'var(--good)') + grp('Already done', r.skipped, 'var(--faint)')
    : grp('Changed', r.done, 'var(--good)') + grp('Left alone', r.skipped, 'var(--faint)');
  if (r.findings && r.findings.length)
    H('bootRes').innerHTML += grp('Checked (nothing changed)', r.findings, '#6ba4e0');
  if (r.attention && r.attention.length)
    H('bootRes').innerHTML += grp('Needs attention', r.attention, 'var(--warn)');
}

/* ---------------- Resources ---------------- */
const RES = [
  ['sfc','System File Checker','Scans every protected Windows file and repairs anything corrupted, using the local component store.'],
  ['dism','Windows Image Repair','Repairs the component store itself with DISM. Run this first if SFC could not fix something.'],
  ['chkdsk','Disk Check','Read-only scan of the system drive for file system errors and bad sectors.']
];
function pageRes() {
  pageShell('Resources', {crumb:'System › Resources',
    text:'Windows setup and repair tools.'},
    `<div class="card" style="margin-bottom:11px">
      <b style="font-size:15px">Windows setup</b>
      <p id="windowsCurrentEdition" style="font-size:13px;margin-top:10px">Checking your Windows version...</p>
      <p id="windowsActivationStatus" style="color:var(--muted);font-size:12px;margin-top:5px" aria-live="polite"></p>
      <p style="color:var(--muted);font-size:12px;margin-top:6px;line-height:1.6">
        Set up Windows after a reset using Microsoft Activation Scripts (MAS 3.12).
        Activation starts the HWID tool in a separate window and needs internet access.
        Change Windows Version opens an in-app chooser for supported editions; it does not
        upgrade Windows 10 to 11. An edition change may require a restart.</p>
      <div class="row" style="margin-top:12px;flex-wrap:wrap">
        <button class="btn" data-windows-setup="activate">Activate Windows</button>
        <button class="btn" data-windows-setup="edition">Change Windows Version</button>
        <button class="btn ghost" id="refreshWindowsStatus">Refresh status</button>
      </div>
      <p id="windowsSetupMessage" role="status" aria-live="polite"
        style="color:var(--muted);font-size:12px;margin-top:10px">
        Bundled from massgravel/Microsoft-Activation-Scripts · GPL-3.0</p>
    </div>` +
    RES.map(([k, t, d]) => `<div class="card" style="margin-bottom:11px">
      <b style="font-size:15px">${t}</b>
      <p style="color:var(--muted);font-size:12px;margin-top:6px;line-height:1.6">${d}</p>
      <div id="res_${k}" style="color:var(--muted);font-size:11.5px;margin-top:10px"></div>
      <div id="prog_${k}" class="jobbar" style="display:none"><i></i></div>
      <div id="verdict_${k}" style="margin-top:10px"></div>
      <div class="row" style="margin-top:12px">
        <button class="btn" data-res="${k}">Run</button>
        <button class="btn ghost" data-cancel="${k}" style="display:none">Cancel</button></div></div>`).join(''));

  wireWindowsSetup();

  RES.forEach(([k]) => {
    const jobkey = 'res:' + k;
    const runBtn = document.querySelector(`[data-res="${k}"]`);
    const cxBtn = document.querySelector(`[data-cancel="${k}"]`);

    const paint = job => {
      const running = job && job.state === 'running';
      runBtn.style.display = running ? 'none' : '';
      cxBtn.style.display = running ? '' : 'none';
      const bar = H('prog_' + k);
      if (bar) {
        bar.style.display = running ? '' : 'none';
        // Real percentage when the tool reports one, animated bar until then.
        const hasPct = running && typeof job.progress === 'number' && job.progress > 0;
        bar.classList.toggle('indet', running && !hasPct);
        const fill = bar.querySelector('i');
        if (fill) fill.style.width = hasPct ? (job.progress * 100) + '%' : '';
      }
      if (running) {
        const pctTxt = (typeof job.progress === 'number' && job.progress > 0)
          ? Math.round(job.progress * 100) + '%  ·  ' : '';
        // Elapsed time proves it is alive even when the tool goes quiet -
        // DISM can sit silent for several minutes mid-repair.
        const el = job.elapsed || 0;
        const mins = Math.floor(el / 60), secs = el % 60;
        const time = el ? '  ·  ' + (mins ? mins + 'm ' : '') + secs + 's' : '';
        H('res_' + k).textContent = pctTxt + (job.line || 'Working...') + time;
        H('verdict_' + k).innerHTML = '';
      } else if (job && job.result) {
        H('res_' + k).textContent = '';
        const r = job.result || {};
        const st = r.state || (job.state === 'cancelled' ? 'cancelled' : 'problem');
        const look = {
          clean:   ['✓', 'var(--good)', 'rgba(61,220,151,.13)'],
          fixed:   ['✓', 'var(--good)', 'rgba(61,220,151,.13)'],
          problem: ['!', 'var(--bad)',  'rgba(255,93,108,.13)'],
          cancelled:['—','var(--muted)','rgba(255,255,255,.06)'],
        }[st] || ['!', 'var(--bad)', 'rgba(255,93,108,.13)'];
        // Never fall back to a bare "Finished." - if the message is missing
        // something went wrong upstream and the user needs to know that.
        const msg = r.message || (st === 'cancelled' ? 'Cancelled before it finished.'
          : 'The scan ended without reporting a result. Check TL-api.log next to the app.');
        H('verdict_' + k).innerHTML =
          `<div style="display:flex;gap:10px;align-items:flex-start;padding:12px 14px;
            border-radius:12px;background:${look[2]};color:${look[1]};font-size:12.5px;
            line-height:1.55"><b style="font-size:14px">${look[0]}</b>
            <span>${msg}</span></div>`;
      }
    };
    JOB_RENDERERS[jobkey] = paint;
    if (JOBS[jobkey]) paint(JOBS[jobkey]);

    runBtn.onclick = async () => {
      H('verdict_' + k).innerHTML = '';
      // Optimistically show the running state at once.
      paint({state: 'running', line: 'Starting...'});
      await api('resource_task', k);
    };
    cxBtn.onclick = () => api('cancel_task', jobkey);
  });
  restoreJobs();
}

/* ---------------- Virtualisation ----------------
   VirtualBox wants VT-x directly. Windows only hands it over when it is not
   running its own hypervisor for VBS / HVCI / WSL2 / Sandbox. This page flips
   between the two states and never touches Secure Boot or TPM, which is what
   kernel anti-cheat actually checks. */
async function pageVirt() {
  pageShell('Virtual Machines', {crumb: 'Tools › Virtual Machines',
    text: 'Give VirtualBox and VMware direct access to the CPU, or hand it back to Windows.'},
    `<div id="virtBody"><div class="card">Reading virtualisation state...</div></div>`);
  await refreshVirt();
}

async function refreshVirt() {
  const st = await api('virt_status');
  if (!st || !H('virtBody')) return;
  window.__virt = st;

  const isVm = st.mode === 'vm';
  const isGame = st.mode === 'gaming';

  const card = (id, active, title, blurb, points, btn) => `
    <button class="bulkbtn modecard ${active ? 'active' : ''}" data-mode="${id}"
      ${active ? 'disabled' : ''}>
      <span class="row" style="align-items:center;gap:9px;width:100%">
        <span class="bt" style="font-size:15.5px">${title}</span>
        ${active ? '<span class="badge on" style="margin-left:auto">ACTIVE NOW</span>' : ''}
      </span>
      <span class="bd" style="font-size:12.5px;color:var(--text)">${blurb}</span>
      <span style="font-size:11.5px;color:var(--muted);line-height:1.7;margin-top:4px">
        ${points.map(p => '• ' + p).join('<br>')}</span>
      <span class="modego">${active ? 'Currently using this' : btn}</span>
    </button>`;

  H('virtBody').innerHTML = `
    ${!st.vt_firmware ? `<div class="card apps-winget-warning" style="margin-bottom:14px;
      border-color:rgba(255,93,108,.35);background:rgba(255,93,108,.1)">
      <b style="color:var(--bad);font-size:13.5px">Virtualisation is turned off in your BIOS</b>
      <p style="color:var(--muted);font-size:12px;line-height:1.65;margin-top:7px">
        No software setting can work around this. Restart, go into your BIOS/UEFI
        at POST, and turn on <b>Intel VT-x</b> (Intel) or <b>SVM Mode</b> (AMD).
        Until then no virtual machine software will run at all.</p></div>` : ''}

    <div class="bulkgrid">
      ${card('vm', isVm, 'Virtual Machines',
        'Pick this to run VirtualBox, VMware or WSL properly.',
        ['VMs run at full speed instead of crawling',
         'Fixes VirtualBox failing to start a machine',
         'Turns off Memory Integrity, so less protection from bad drivers'],
        'Set up for virtual machines')}
      ${card('gaming', isGame, 'Gaming &amp; Normal Use',
        'Pick this for everyday use and playing games.',
        ['Secure Boot and TPM untouched — what anti-cheat checks',
         'Memory Integrity stays off, so installers and games stay fast',
         'Virtual machines still run, just slower'],
        'Set up for gaming')}
    </div>
    <div id="virtMsgWrap" class="bulkstatus" hidden><span id="virtMsg"></span></div>

    <div class="section">DETAILS</div>
    <div class="card">
      <div class="row" style="gap:10px;margin:4px 0;font-size:12.5px">
        <span style="color:var(--muted);flex:1">Windows hypervisor at boot</span>
        <span>${st.launchtype === 'off' ? 'Off' : 'On'}</span></div>
      <div class="row" style="gap:10px;margin:4px 0;font-size:12.5px">
        <span style="color:var(--muted);flex:1">Memory Integrity</span>
        <span>${st.hvci ? 'On' : 'Off'}</span></div>
      <div class="row" style="gap:10px;margin:4px 0;font-size:12.5px">
        <span style="color:var(--muted);flex:1">VirtualBox</span>
        <span>${st.virtualbox ? (st.virtualbox_version || 'Installed') : 'Not installed'}</span></div>
      <div class="row" style="gap:10px;margin:4px 0;font-size:12.5px">
        <span style="color:var(--muted);flex:1">Secure Boot &amp; TPM (what anti-cheat checks)</span>
        <span style="color:var(--good)">${
          st.secureboot === true && st.tpm === true ? 'Both on — never changed here'
          : 'Not changed by this page'}</span></div>
      <p style="color:var(--muted);font-size:11.5px;line-height:1.65;margin-top:12px">
        Neither button touches Secure Boot or TPM — those are the firmware
        settings anti-cheat looks at. <b>Memory Integrity is left off by
        both</b>, because turning it on taxes every driver load and makes
        installers crawl. One exception worth knowing: <b>Valorant can ask for
        Memory Integrity to be on</b> — if Vanguard complains, switch it on in
        Windows Security &gt; Device security &gt; Core isolation, and this app
        will leave it alone. <b>Either choice needs a restart.</b></p>
    </div>`;

  document.querySelectorAll('[data-mode]').forEach(b => {
    b.onclick = () => confirmVirt(b.dataset.mode);
  });
}

function confirmVirt(mode) {
  const vm = mode === 'vm';
  showModal(`<div class="modal-card">
      <h2 style="margin:0 0 10px;font-size:18px">
        ${vm ? 'Set this PC up for virtual machines?' : 'Set this PC up for gaming?'}</h2>
      <p style="color:var(--muted);font-size:12.5px;line-height:1.7;margin:0 0 12px">
        ${vm ? 'VirtualBox and VMware will get full use of your CPU, so machines '
             + 'run at proper speed. The trade is that Windows Memory Integrity '
             + 'gets switched off, which is what blocks dodgy drivers from loading.'
             : 'Puts the machine back to normal for gaming and everyday use. '
             + 'Memory Integrity is left OFF either way, so nothing here will '
             + 'slow your installers or games down. Virtual machines still run, '
             + 'just slower.'}</p>
      <p style="color:var(--muted);font-size:12px;line-height:1.6;margin:0 0 14px">
        Secure Boot and TPM are not touched. <b>You need to restart for this to
        take effect</b> — and you can switch back whenever you like.</p>
      <div class="row" style="gap:10px">
        <button class="btn" id="vtYes">${vm ? 'Set up for VMs' : 'Set up for gaming'}</button>
        <button class="btn ghost" id="vtNo">Cancel</button>
      </div></div>`);
  H('vtYes').onclick = async () => {
    closeModal();
    const wrap = H('virtMsgWrap');
    if (wrap) { wrap.hidden = false; H('virtMsg').textContent = 'Applying...'; }
    const r = await api('virt_set', mode);
    await refreshVirt();
    const w2 = H('virtMsgWrap');
    if (w2) {
      w2.hidden = false;
      H('virtMsg').innerHTML = (r && r.ok)
        ? '<b style="color:var(--good)">Done — restart your PC to finish.</b>'
        : '<b style="color:var(--warn)">' + ((r && r.message) || 'Could not apply.') + '</b>';
    }
  };
  H('vtNo').onclick = closeModal;
}

/* ---------------- Install Apps ----------------
   Mirrors the useful half of a toolbox like Ghost's: pick an app, it is
   fetched and installed silently. winget does the work where it exists
   (Microsoft keeps those URLs and switches current); otherwise the app falls
   back to a direct download from the vendor's own domain. */
let APPCACHE = null;
let APP_GROUP = 'File tools';
function appIcon(id) {
  const labels = {shiftd: 'S', vcredist: 'C++', directx: 'DX', dotnet8: '.NET'};
  return labels[id]
    ? `<span class="app-icon app-icon-${id}" aria-hidden="true">${labels[id]}</span>`
    : `<span class="app-icon app-brand-icon" aria-hidden="true">${APP_BRAND_ICONS[id] || icon('box')}</span>`;
}

async function pageApps() {
  pageShell('Install Apps', {crumb: 'Tools › Install Apps',
    text: 'File conversion, archive extraction, runtimes, browsers, game clients and Discord setup.'},
    `<div id="appsBody"><div class="card">Loading the catalogue...</div></div>`);
  const cat = APPCACHE || await api('app_catalog');
  if (!cat) return;
  APPCACHE = cat;

  const groups = cat.groups.map(g => {
    const items = cat.apps.filter(a => a.group === g);
    if (!items.length) return '';
    return `<section class="app-group" data-app-group="${g}" ${g === APP_GROUP ? "" : "hidden"} aria-label="${g}">
      <div class="apps-grid">${items.map(a => `
        <div class="card appcard" data-app="${a.id}">
          <div class="app-heading">
            ${appIcon(a.id)}
            <div style="flex:1;min-width:0">
              <b style="font-size:14.5px">${a.name}</b>
              <p class="app-description" title="${a.desc.replaceAll('"', '&quot;')}">${a.desc}</p>
            </div>
            <span class="badge" title="${a.route === 'winget'
              ? 'Installed through the Windows Package Manager'
              : (a.route === 'direct' ? 'Downloaded straight from the vendor'
                                      : 'No automatic route - opens the vendor page')}"
              >${a.route === 'winget' ? 'WINGET' : (a.route === 'direct' ? 'DIRECT' : 'MANUAL')}</span>
          </div>
          <div id="appline_${a.id}" class="app-status"></div>
          <div class="jobbar" id="appbar_${a.id}" style="display:none"><i></i></div>
          <div id="appres_${a.id}" class="app-result"></div>
          <div class="row app-actions">
            ${a.installable ? `<button class="btn" data-inst="${a.id}">Install</button>` : ''}
            <button class="btn ghost" data-cancelapp="${a.id}" style="display:none">Cancel</button>
            <button class="btn ghost" onclick="api('open_url','${a.page}')">Vendor page</button>
          </div>
        </div>`).join('')}</div></section>`;
  }).join('');

  H('appsBody').innerHTML = `
    ${cat.winget ? '' : `<p class="apps-winget-warning">Windows Package Manager is missing. DIRECT apps still install; use the vendor page for MANUAL entries.</p>`}
    <div class="apps-categories" role="group" aria-label="App categories">
      ${cat.groups.map(g => `<button class="btn ghost" data-app-category="${g}" aria-pressed="${g === APP_GROUP}">${g}</button>`).join('')}
    </div>
    ${storeCardHtml()}
    ${groups}
    <details class="apps-note"><summary>Installer sources and Discord setup</summary><p style="color:var(--muted);font-size:11.5px;line-height:1.65">
      Installers come from their vendor or Windows Package Manager and use
      official silent switches. The Discord card also downloads the unmodified
      OpenAsar nightly from its official GitHub release and verifies GitHub's
      SHA-256 digest before replacing Discord's app.asar. Nothing is bundled or
      repacked.</p></details>`;

  document.querySelectorAll('[data-app-category]').forEach(button => {
    button.onclick = () => {
      APP_GROUP = button.dataset.appCategory;
      document.querySelectorAll('[data-app-category]').forEach(b => b.setAttribute('aria-pressed', b === button));
      document.querySelectorAll('[data-app-group]').forEach(panel => panel.hidden = panel.dataset.appGroup !== APP_GROUP);
      H('storeCard').hidden = APP_GROUP !== 'File tools';
      H('scroll').scrollTop = 0;
    };
  });
  H('storeCard').hidden = APP_GROUP !== 'File tools';
  wireApps(cat);
  wireStoreCard();
  restoreJobs();
}

function wireApps(cat) {
  cat.apps.forEach(a => {
    const jobkey = 'app:' + a.id;
    const btn = document.querySelector(`[data-inst="${a.id}"]`);
    const cx = document.querySelector(`[data-cancelapp="${a.id}"]`);
    if (!btn && !cx) return;

    const paint = job => {
      const running = job && job.state === 'running';
      if (btn) btn.style.display = running ? 'none' : '';
      if (cx) cx.style.display = running ? '' : 'none';
      const bar = H('appbar_' + a.id);
      if (bar) {
        bar.style.display = running ? '' : 'none';
        const hasPct = running && typeof job.progress === 'number' && job.progress > 0;
        bar.classList.toggle('indet', running && !hasPct);
        const fill = bar.querySelector('i');
        if (fill) fill.style.width = hasPct ? (job.progress * 100) + '%' : '';
      }
      if (running) {
        const el = job.elapsed || 0;
        const t = el ? '  ·  ' + (el >= 60 ? Math.floor(el / 60) + 'm ' : '') + (el % 60) + 's' : '';
        H('appline_' + a.id).textContent = (job.line || 'Working...') + t;
        H('appres_' + a.id).innerHTML = '';
      } else if (job && job.result) {
        H('appline_' + a.id).textContent = '';
        const r = job.result, good = r.ok;
        H('appres_' + a.id).innerHTML =
          `<div style="display:flex;gap:9px;padding:9px 11px;border-radius:10px;
            font-size:12px;line-height:1.5;background:${good ? 'rgba(61,220,151,.13)' : 'rgba(255,93,108,.13)'};
            color:${good ? 'var(--good)' : 'var(--bad)'}">
            <b>${good ? '✓' : '!'}</b><span>${r.message || 'Finished.'}</span></div>`;
      }
    };
    JOB_RENDERERS[jobkey] = paint;
    if (JOBS[jobkey]) paint(JOBS[jobkey]);

    if (btn) btn.onclick = async () => {
      H('appres_' + a.id).innerHTML = '';
      paint({state: 'running', progress: 0, line: 'Starting...'});
      await api('app_install', a.id);
    };
    if (cx) cx.onclick = () => api('cancel_app', jobkey);
  });
}

/* ---- Microsoft Store & Xbox ---- */
function storeCardHtml() {
  return `<div class="card" id="storeCard" style="margin-bottom:6px">
    <div class="row" style="align-items:flex-start;gap:14px">
      <div style="flex:1">
        <b style="font-size:15px">Microsoft Store &amp; Xbox apps</b>
        <p id="storeState" style="color:var(--muted);font-size:12px;margin-top:5px">Checking...</p>
      </div>
    </div>
    <div class="row" style="margin-top:13px;gap:9px;flex-wrap:wrap">
      <button class="btn" id="storeOn">Install / restore</button>
      <button class="btn ghost" id="storeOff">Remove both</button>
      <button class="btn ghost" id="storeGet" style="display:none">Get from Microsoft</button>
      <span id="storeMsg" style="color:var(--muted);font-size:11.5px"></span>
    </div></div>`;
}

async function wireStoreCard() {
  const paint = st => {
    if (!st || !H('storeState')) return;
    const bits = [];
    bits.push('Microsoft Store: ' + (st.store ? 'installed' : 'not installed'));
    bits.push('Xbox apps: ' + (st.xbox ? 'installed' : 'not installed'));
    H('storeState').textContent = bits.join('   ·   ');
    H('storeState').style.color = (st.store || st.xbox) ? 'var(--good)' : 'var(--muted)';
  };
  paint(await api('store_status'));

  const getBtn = H('storeGet');
  H('storeOn').onclick = async () => {
    H('storeMsg').textContent = 'Installing from Microsoft...'; H('storeMsg').style.color = 'var(--muted)';
    if (getBtn) getBtn.style.display = 'none';
    const r = await api('store_set', 'both', true);
    paint(r && r.status);
    if (r && r.ok) {
      H('storeMsg').textContent = (r.via === 'winget') ? 'Installed from Microsoft.' : 'Done.';
      H('storeMsg').style.color = 'var(--good)';
    } else {
      H('storeMsg').textContent = (r && r.message) || 'Could not restore them.';
      H('storeMsg').style.color = 'var(--warn)';
      // Always give a working way forward when the automatic route fails.
      if (getBtn) {
        const url = (r && r.store_url) || 'https://apps.microsoft.com/detail/9wzdncrfjbmp';
        getBtn.style.display = '';
        getBtn.onclick = () => api('open_url', url);
      }
    }
  };
  H('storeOff').onclick = () => {
    showModal(`<div class="modal-card">
      <h2 style="margin:0 0 8px;font-size:18px;color:var(--warn)">Remove Store and Xbox apps?</h2>
      <p style="color:var(--muted);font-size:12.5px;line-height:1.6;margin:0 0 14px">
        Removes the Microsoft Store, Xbox Game Bar and the Xbox app for this
        user. On a normal Windows install they can be restored from here.
        <b>On a debloated image they may not come back</b>, because Windows
        keeps no copy to restore from.</p>
      <div class="row" style="gap:10px">
        <button class="btn" id="stYes">Remove</button>
        <button class="btn ghost" id="stNo">Cancel</button>
      </div></div>`);
    H('stYes').onclick = async () => {
      closeModal();
      H('storeMsg').textContent = 'Removing...';
      const r = await api('store_set', 'both', false);
      paint(r && r.status);
      H('storeMsg').textContent = 'Removed.';
      H('storeMsg').style.color = 'var(--muted)';
    };
    H('stNo').onclick = closeModal;
  };
}

/* ---------------- BIOS ---------------- */
let BIOSCACHE = null;
async function pageBios() {
  pageShell('Firmware & BIOS', {crumb:'Tools › BIOS Info',
    text:'What Windows can see about your firmware.'},
    `<div id="biosBody"><div class="card">Reading...</div></div>`);
  const d = BIOSCACHE || await api('bios_info');
  if (!d) return;
  BIOSCACHE = d;
  H('biosBody').innerHTML = `
    <div class="card" style="margin-bottom:14px;${d.supported
      ? 'border-color:rgba(61,220,151,.3)' : ''}">
      <b style="color:${d.supported ? 'var(--good)' : '#6ba4e0'};font-size:12.5px">
      ${d.supported ? 'Vendor BIOS interface available: ' + d.label
        : 'Read-only - this board has no supported Windows interface for changing BIOS settings'}</b></div>
    <div class="grid g3">${d.rows.map(([k, v]) => `<div class="card">
      <div class="label">${k}</div>
      <div style="font-weight:600;font-size:13px;margin-top:4px">${v}</div></div>`).join('')}</div>
    <div class="card" style="margin-top:14px"><p style="color:var(--muted);font-size:11.5px;line-height:1.65">
      Why this is read-only: Dell, HP and Lenovo publish supported WMI interfaces for
      changing BIOS settings from Windows, and this app uses them when it finds one.
      Consumer boards publish nothing equivalent - the only way in is writing firmware
      NVRAM through an undocumented driver, and a bad write bricks the board with no
      way back.</p></div>`;
}

/* ---------------- System Restore ---------------- */
function pageRestore() {
  pageShell('System Restore', {crumb:'Tools › System Restore',
    text:'Make a safety net before you tweak.'},
    `<div class="card"><p style="color:var(--muted);font-size:12.5px;line-height:1.65">
      Create a Windows restore point before applying tweaks. If anything misbehaves
      you can roll the whole system back from Windows Recovery.</p>
      <div class="row" style="margin-top:15px">
        <button class="btn" id="rpBtn">Create Restore Point</button>
        <span id="rpMsg" style="color:var(--muted);font-size:12px"></span></div></div>`);
  H('rpBtn').onclick = async () => {
    H('rpBtn').disabled = true; H('rpBtn').textContent = 'Creating...';
    const r = await api('restore_point');
    H('rpBtn').disabled = false; H('rpBtn').textContent = 'Create Restore Point';
    H('rpMsg').textContent = (r && r.message) ||
      (r && r.ok ? 'Restore point created.' : 'Could not create one.');
    H('rpMsg').style.color = r && r.ok ? 'var(--good)' : 'var(--warn)';
  };
}

/* ---------------- Networking: test + tweaks in one page ---------------- */
const TIPS = {
  bloat: ['Bufferbloat - the lag spike when your line gets busy',
    'Your router holds packets in a queue when the connection is full. Ping looks fine idle, then jumps the moment someone streams. This grade is how much your ping rose while the line was saturated. Higher grade is better.',
    'A or better and you will barely notice it. C or worse is worth fixing with Smart Queue / SQM on your router - no Windows tweak can fix bufferbloat.'],
  speed: ['Download and upload speed',
    'How much data your line moves per second, measured over parallel connections once TCP has settled. Higher is better.',
    'Gaming needs surprisingly little - 25 Mbps down is plenty. Speed is not what causes lag; latency and jitter are.'],
  lat: ['Ping - how long a round trip takes',
    'Measured idle, then again while the line is saturated in each direction. Lower is better. The gap between idle and loaded is the bufferbloat.',
    'Under 20 ms idle is great. You want loaded to stay within about 30 ms of idle.'],
  jit: ['Jitter - how steady your ping is',
    'Ping says how far the server feels. Jitter says how much that wobbles packet to packet. High jitter is what makes a game feel rubber-bandy even when ping looks fine. Lower is better.',
    'Under 5 ms is excellent, over 20 ms you will feel it. Two numbers means idle / under load.'],
  conn: ['What your connection can actually handle',
    'Each row checks your measured speed and loaded ping against what that activity really needs. A tick means comfortably above; a cross means it would stutter; a ? means that direction could not be measured.',
    'Low latency gaming is the strictest row - it wants loaded ping under about 75 ms.'],
};
const tipAttr = k => `data-t="${TIPS[k].join('|').replace(/"/g,'&quot;')}"`;

function pageNetworking() {
  const items = STATE.tweaks.filter(t => t.category === 'Networking');
  pageShell('Networking', {crumb:'Tweaks › Networking',
    text:'Test your connection, then tune it.'},
    `<div class="row" style="margin-bottom:14px">
      <button class="btn" id="netRun">Run Test</button>
      <button class="btn ghost" onclick="netBulk(true)">Optimize Network</button>
      <button class="btn ghost" onclick="netBulk(false)">Revert Network</button>
      <div class="spacer"></div>
      <span id="netStatus" style="color:var(--muted);font-size:11.5px">Saturates the line for about 30 seconds.</span></div>
     <div class="bar" style="margin-bottom:16px"><i id="netBar"></i></div>
     <div class="grid network-metrics">
       <div class="card"><div class="label">BUFFERBLOAT GRADE <span class="info" ${tipAttr('bloat')}>?</span></div>
         <div style="display:flex;align-items:center;gap:16px;margin-top:14px">
           <b id="grade" style="font-size:44px;color:var(--muted)">—</b>
           <div style="flex:1"><div class="bar" id="gradeMeter" role="meter" aria-label="Bufferbloat grade" aria-valuemin="0" aria-valuemax="6" aria-valuetext="Run a test" style="height:22px;border-radius:11px">
             <i id="gradeBar" style="width:0%;background:linear-gradient(90deg,var(--accent),var(--accent-2))"></i></div></div></div>
         <div class="grade-legend" aria-label="Bufferbloat grades: added latency under load"><span class="grade-caption">Added latency (ms):</span><span><b>A+</b> &lt;5</span><span><b>A</b> 5–&lt;30</span><span><b>B</b> 30–&lt;60</span><span><b>C</b> 60–&lt;200</span><span><b>D</b> 200–&lt;400</span><span><b>F</b> ≥400</span></div>
         <p id="verdict" style="color:var(--muted);font-size:12px;margin-top:12px">Run a test to measure your connection.</p></div>
       <div class="card"><div class="label">INTERNET SPEED <span class="info" ${tipAttr('speed')}>?</span></div>
         <div style="margin-top:14px"><div class="row"><span style="color:var(--muted);font-size:11.5px">Download</span>
           <div class="spacer"></div><b id="dl" style="font-size:18px">—</b></div>
           <div class="bar"><i id="dlBar"></i></div></div>
         <div style="margin-top:14px"><div class="row"><span style="color:var(--muted);font-size:11.5px">Upload</span>
           <div class="spacer"></div><b id="ul" style="font-size:18px">—</b></div>
           <div class="bar"><i id="ulBar" style="background:linear-gradient(90deg,var(--accent),var(--accent-2))"></i></div></div></div>
       <div class="card"><div class="label">LATENCY <span class="info" ${tipAttr('lat')}>?</span></div>
         <div class="row" style="margin-top:14px;gap:20px">
           ${['Idle','Download','Upload'].map((n, i) => `<div><div style="font-size:10px;color:var(--faint)">${n}</div>
             <b id="lat${i}" style="font-size:21px">—</b></div>`).join('')}</div>
         <div class="row" style="margin-top:14px"><span style="color:var(--muted);font-size:11.5px">Jitter
           <span class="info" ${tipAttr('jit')}>?</span></span>
           <div class="spacer"></div><b id="jit" style="font-size:15px">—</b></div></div>
     </div>
     <div class="card network-activities"><div class="label">YOUR CONNECTION <span class="info" ${tipAttr('conn')}>?</span></div>
       <div id="connRows" style="margin-top:12px"></div></div>
     <div class="section">NETWORK TWEAKS</div>
     <div class="grid g3" id="netTweakGrid"></div>`);
  renderTweaksInto(items, 'Networking');
  H('netRun').onclick = runNetTest;
  const acts = ['Web browsing','Audio calls','4K video streaming','Video conferencing','Low latency gaming'];
  H('connRows').innerHTML = acts.map((a, i) =>
    `<div class="row" style="padding:6px 0"><span style="font-size:12.5px">${a}</span>
     <div class="spacer"></div><span id="cr${i}" class="badge">—</span></div>`).join('');
  wireTips();
  restoreNetView();
}
function renderTweaksInto(items, cat) {
  const g = H('netTweakGrid'); if (!g) return;
  g.innerHTML = items.map(t => `
    <div class="card tweak ${t.applied ? 'on' : ''}" data-key="${t.key}">
      <div class="top"><div class="ico">${svg(t.icon || 'net')}</div><h3>${t.name}</h3></div>
      <div class="desc">${t.desc}</div>
      ${t.warning ? `<div class="warnpill">▲ ${t.warning}</div>` : ''}
      <div class="foot"><span class="badge ${t.applied ? 'on' : ''}">
        ${t.applied == null ? 'UNKNOWN' : t.applied ? 'APPLIED' : 'NOT APPLIED'}</span>
        <button type="button" class="sw ${t.applied ? 'on' : ''}" data-sw="${t.key}" role="switch" aria-checked="${t.applied === true}" aria-label="${t.name}"></button></div>
      </div>`).join('');
  document.querySelectorAll('[data-sw]').forEach(sw => {
    sw.onclick = () => setToggle(sw.dataset.sw);
  });
}
async function netBulk(on) {
  return applyCategory('Networking', on);
}
const fmtSpeed = m => !m ? '—' : (m >= 1000 ? (m / 1000).toFixed(2) + ' Gbps' : Math.round(m) + ' Mbps');
const NET_JOB = { running:false, result:null, progress:null, partial:null };
function restoreNetView() {
  if (!H('netRun')) return;
  H('netRun').hidden = NET_JOB.running;
  if (NET_JOB.progress) {
    H('netStatus').textContent = NET_JOB.progress.label + '...';
    H('netBar').style.width = Math.min(100, NET_JOB.progress.frac * 100) + '%';
  }
  if (NET_JOB.partial) paintNet(NET_JOB.partial.res, NET_JOB.partial.stage);
  if (NET_JOB.result) paintNetResult(NET_JOB.result);
}
window.py_netprogress = d => {
  NET_JOB.progress = d;
  if (H('netStatus')) H('netStatus').textContent = d.label + '...';
  if (H('netBar')) H('netBar').style.width = Math.min(100, d.frac * 100) + '%';
};
window.py_netpartial = d => { NET_JOB.partial = d; paintNet(d.res, d.stage); };
function paintNet(r, stage) {
  const ms = v => v ? Math.round(v) + ' ms' : '—';
  if (r.idle && H('lat0')) H('lat0').textContent = ms(r.idle.med);
  if (stage === 'download' || r.down) {
    if (H('dl')) { H('dl').textContent = fmtSpeed(r.download_mbps);
      H('dlBar').style.width = Math.min(100, (r.download_mbps || 0) / 2500 * 100) + '%'; }
    if (r.down && H('lat1')) H('lat1').textContent = ms(r.down.med);
  }
  if (stage === 'upload' || r.up) {
    if (H('ul')) { H('ul').textContent = fmtSpeed(r.upload_mbps);
      H('ulBar').style.width = Math.min(100, (r.upload_mbps || 0) / 1000 * 100) + '%'; }
    if (r.up && H('lat2')) H('lat2').textContent = ms(r.up.med);
  }
}
async function runNetTest() {
  if (NET_JOB.running) return;
  Object.assign(NET_JOB, {running:true, result:null, progress:null, partial:null});
  H('netRun').hidden = true;
  H('netStatus').textContent = 'Starting connection test...';
  H('netStatus').style.color = 'var(--muted)';
  ['netBar','dlBar','ulBar'].forEach(id => { H(id).style.width = '0%'; });
  ['lat0','lat1','lat2','dl','ul','jit'].forEach(i => { if (H(i)) H(i).textContent = '—'; });
  H('grade').textContent = '—';
  H('gradeBar').style.width = '0%';
  H('gradeMeter').removeAttribute('aria-valuenow');
  H('gradeMeter').setAttribute('aria-valuetext','Test running');
  let r;
  try { r = await api('nettest'); }
  catch (error) { r = {error:String(error)}; }
  NET_JOB.running = false;
  NET_JOB.result = r || {error:'Test failed'};
  restoreNetView();
}
function paintNetResult(r) {
  if (!H('netRun')) return;
  H('netRun').hidden = false; H('netRun').textContent = 'Test again';
  H('netStatus').style.color = 'var(--muted)';
  if (!r || r.error) { H('netStatus').textContent = (r && r.error) || 'Test failed';
    H('netStatus').style.color = 'var(--warn)'; return; }
  paintNet(r, 'all');
  const ms = v => v ? Math.round(v) + ' ms' : '—';
  const j = r.idle_jitter, lj = r.jitter_ms;
  H('jit').textContent = (lj && j && lj > j * 1.5) ? `${Math.round(j)} / ${Math.round(lj)} ms` : ms(j);
  H('jit').style.color = j == null ? 'var(--text)' : (j < 5 ? 'var(--good)' : j < 20 ? 'var(--warn)' : 'var(--bad)');
  (r.activities || []).forEach(([n, ok], i) => {
    const el = H('cr' + i); if (!el) return;
    el.innerHTML = svg(ok === null ? 'help' : ok ? 'check' : 'close');
    el.setAttribute('aria-label', n + ': ' + (ok === null ? 'Not measured' : ok ? 'Suitable' : 'Not suitable'));
    el.className = 'badge ' + (ok ? 'on' : '');
    if (ok === false) el.style.cssText = 'background:rgba(255,93,108,.14);color:var(--bad)';
  });
  const rank = { 'A+':6, A:5, B:4, C:3, D:2, F:1 }[r.grade] || 0;
  H('gradeBar').style.width = (rank / 6 * 100) + '%';
  H('gradeMeter').setAttribute('aria-valuenow',String(rank));
  H('gradeMeter').setAttribute('aria-valuetext',rank ? `Grade ${r.grade}${Number.isFinite(r.increase_ms) ? ': ' + r.increase_ms.toFixed(1) + ' ms added latency' : ''}` : 'Grade unavailable');
  H('grade').textContent = r.grade;
  H('grade').style.color = ['A+','A','B'].includes(r.grade) ? 'var(--good)'
    : ['C','D'].includes(r.grade) ? 'var(--warn)' : 'var(--bad)';
  H('verdict').textContent = r.verdict + ` (base ping ${Math.round(r.idle_ms)} ms)`;
  H('netStatus').textContent = r.increase_ms != null
    ? `Latency rose ${Math.round(r.increase_ms)} ms under load.` : 'Done.';
}

/* ---------- window dragging ----------------------------------------
   One bridge call on mousedown, then Windows owns the gesture. The old
   pywebview drag-region called into Python on every mousemove, which is
   what made dragging look like ~30fps on a 240Hz screen. */
(function wireDrag() {
  const tb = document.getElementById('titlebar');
  if (!tb) return;
  const onControls = e => !!(e.target.closest && e.target.closest('#winbtns'));

  // pywebview's own drag-region (the .pywebview-drag-region class in the HTML)
  // does the actual window move - that is what reliably works inside WebView2.
  // We only add/remove the .dragging class so the expensive aurora/backdrop
  // effects freeze for the duration, which is what keeps the move smooth.
  // pywebview's move fires mousemove DURING the drag, so clear only on mouseup.
  const endDrag = () => document.body.classList.remove('dragging');
  window.addEventListener('mouseup', endDrag, true);
  window.addEventListener('blur', endDrag);

  tb.addEventListener('mousedown', e => {
    if (e.button !== 0 || onControls(e)) return;
    document.body.classList.add('dragging');
    setTimeout(endDrag, 6000);   // safety net
  });

  tb.addEventListener('dblclick', e => {
    if (onControls(e)) return;
    changeAppWindow('maximize');
  });
})();


/* ---------- generic confirm modal ---------- */
let modalReturnFocus = null;
function showModal(html) {
  let o = document.getElementById('modal');
  if (!o) { o = document.createElement('div'); o.id = 'modal';
            o.className = 'modal-overlay'; document.body.appendChild(o); }
  if (!o.classList.contains('show') || o.inert) modalReturnFocus = document.activeElement;
  o.innerHTML = html; o.classList.add('show'); o.classList.remove('closing'); o.inert = false;
  animatePanel(o, true, undefined, true);
  const card = o.querySelector('.modal-card');
  if (card) animatePanel(card, true);
  o.setAttribute('role','dialog'); o.setAttribute('aria-modal','true');
  o.setAttribute('aria-label',o.querySelector('h2,h3')?.textContent || 'Confirm action');
  H('shell').inert = true;
  const controls = () => [...o.querySelectorAll('button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled),[tabindex="0"]')].filter(e => e.getClientRects().length);
  o.tabIndex = -1;
  (controls().find(e => /^cancel$/i.test(e.textContent.trim())) || controls()[0] || o).focus();
  o.onkeydown = e => {
    if (e.key === 'Escape') { e.preventDefault(); closeModal(); return; }
    if (e.key !== 'Tab') return;
    const list = controls(), first = list[0], last = list[list.length-1];
    if (!first) { e.preventDefault(); o.focus(); }
    else if (e.shiftKey && (document.activeElement === first || document.activeElement === o)) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  };
  o.onclick = e => { if (e.target === o) closeModal(); };
}
function closeModal() {
  const o = document.getElementById('modal');
  if (o && !o.inert) {
    o.inert = true; o.classList.add('closing');
    const card = o.querySelector('.modal-card');
    if (card) animatePanel(card, false);
    animatePanel(o, false, () => { o.classList.remove('show', 'closing'); o.innerHTML = ''; }, true);
  }
  H('shell').inert = false;
  if (modalReturnFocus?.isConnected) modalReturnFocus.focus();
  modalReturnFocus = null;
}

/* ---------- Windows Defender page ---------- */
async function pageDefender() {
  pageShell('Windows Defender', {crumb: 'System › Defender',
    text: 'Turn Microsoft Defender fully on or off. Reads the live state from this PC.'},
    `<div class="card" id="defCard">
       <div class="row" style="align-items:flex-start">
         <div style="flex:1">
           <b style="font-size:16px">Microsoft Defender</b>
           <p id="defState" style="color:var(--muted);font-size:12.5px;margin-top:6px">Reading current state...</p>
         </div>
         <button type="button" class="sw" id="defTgl" role="switch" aria-label="Microsoft Defender" aria-checked="false" disabled></button>
       </div>
       <div id="defTamper"></div>
       <div id="defList" style="margin-top:16px"></div>
       <p style="color:var(--muted);font-size:11.5px;line-height:1.6;margin-top:16px">
         Turning Defender off leaves this PC with no antivirus until you turn it
         back on. Only do this if you run something else or accept the risk.
         Everything here is undone by the same toggle.</p>
     </div>

     <div class="card" id="defRemoveCard" style="margin-top:14px;border-color:rgba(255,93,108,.28)">
       <b style="font-size:14px;color:var(--bad)">Permanently remove Defender</b>
       <p style="color:var(--muted);font-size:11.5px;line-height:1.65;margin-top:7px">
         Use the integrated <b>Defender Remover</b> controls to remove Defender
         and Windows Security. Its removal also disables other Windows protections,
         including SmartScreen, UAC and security mitigations. Recovery may require
         reinstalling Windows. Choose a removal option and review its scope before proceeding.</p>
       <div class="row" style="margin-top:11px">
         <button class="btn ghost" id="defRemove"
           style="border-color:rgba(255,93,108,.4);color:var(--bad)">Removal options</button>
       </div>
     </div>`);
  await refreshDefender();
  const rm = H('defRemove');
  if (rm) rm.onclick = openDefenderRemoval;
}

async function refreshDefender() {
  const st = await api('defender_status');
  if (!st) return;
  window.__def = st;
  const tgl = H('defTgl');
  if (tgl) { tgl.classList.toggle('on', !!st.active);
    tgl.setAttribute('aria-checked',String(!!st.active)); tgl.disabled = !st.present; }
  const state = H('defState');
  if (state) {
    state.textContent = !st.present
      ? 'Defender antivirus is not detected. Windows Security and leftover files are checked separately in Removal options.'
      : (st.active ? 'Defender is ON and protecting this PC.' : 'Defender is OFF.');
    state.style.color = st.active ? 'var(--good)' : 'var(--warn)';
  }
  const list = H('defList');
  if (list) {
    let html = (st.items || []).map(it =>
      `<div class="row" style="gap:9px;margin:5px 0;font-size:12.5px">
         <span style="width:9px;height:9px;border-radius:50%;flex:0 0 auto;
           background:${it.on ? 'var(--good)' : 'var(--warn)'}"></span>
         <span style="color:var(--text)">${it.label}</span>
         <span class="spacer"></span>
         <span style="color:${it.on ? 'var(--good)' : 'var(--muted)'}">${it.on ? 'On' : 'Off'}</span>
       </div>`).join('');
    // The antimalware service stays resident even with everything above off.
    // Show it, but make clear it is not something the toggle failed to turn
    // off - Windows keeps it running and no tool can stop it.
    if (st.engine_resident && !st.active) {
      html += `<div style="margin-top:11px;padding:9px 11px;border-radius:9px;
        background:rgba(255,255,255,.04);font-size:11.5px;line-height:1.55;color:var(--muted)">
        The antimalware service is still resident in memory. That is normal —
        Windows keeps it loaded and nothing can unload it while Defender is the
        installed antivirus. With real-time protection off it is not scanning.</div>`;
    }
    list.innerHTML = html;
  }
  const tam = H('defTamper');
  if (tam) tam.innerHTML = (st.tamper && st.active)
    ? `<div style="margin-top:12px;padding:10px 12px;border-radius:10px;
         background:rgba(255,190,61,.12);border:1px solid rgba(255,190,61,.3);
         color:var(--warn);font-size:12px;line-height:1.55">
         <b>Tamper Protection is on.</b> Windows blocks every app — this one
         included — from switching Defender off while it is. Tapping the
         toggle opens the exact Windows Security page so you can flip that one
         switch yourself; the app finishes the rest.</div>` : '';
  if (tgl) tgl.onclick = () => confirmDefender(!st.active);
}

function confirmDefender(want) {
  const st = window.__def || {};
  if (!st.present) return;
  const changed = ['Real-time protection', 'Behaviour monitoring',
    'On-access scanning', 'Downloaded-file & web scanning', 'Network inspection',
    want ? 'Security notifications restored'
         : 'The "your PC isn\'t protected" notifications'];
  const verb = want ? 'TURNED BACK ON' : 'TURNED OFF';
  showModal(`<div class="modal-card">
      <h2 style="margin:0 0 8px;font-size:18px;color:${want ? 'var(--good)' : 'var(--warn)'}">
        ${want ? 'Turn Windows Defender ON?' : 'Turn Windows Defender OFF?'}</h2>
      <p style="color:var(--muted);font-size:12.5px;line-height:1.6;margin:0 0 14px">
        ${want ? 'This restores Microsoft Defender to full protection.'
               : 'This leaves the PC with no antivirus until you turn it back on. All of it is reversible.'}</p>
      <div style="font-size:10.5px;color:var(--muted);letter-spacing:.07em;margin-bottom:7px">WILL BE ${verb}</div>
      ${changed.map(l => `<div style="font-size:12.5px;margin:5px 0;color:var(--text)">• ${l}</div>`).join('')}
      ${(!want && st.tamper) ? `<div style="margin-top:12px;font-size:12px;color:var(--warn);line-height:1.5">
        Tamper Protection is on, so Windows Security will open first for you to
        switch it off — then tap the toggle once more.</div>` : ''}
      <div class="row" style="margin-top:20px;gap:10px">
        <button class="btn" id="defYes">${want ? 'Turn On' : 'Turn Off'}</button>
        <button class="btn ghost" id="defNo">Cancel</button>
      </div>
    </div>`);
  H('defYes').onclick = async () => {
    closeModal();
    if (H('defState')) { H('defState').textContent = 'Working...'; H('defState').style.color = 'var(--muted)'; }
    const r = await api('defender_set', want);
    if (r && r.tamper && H('defState')) {
      H('defState').textContent = r.message || 'Turn Tamper Protection off, then tap again.';
      H('defState').style.color = 'var(--warn)';
      if (window.__def) window.__def = r.status || window.__def;
      const tgl = H('defTgl'); if (tgl) tgl.classList.add('on');
      return;
    }
    await refreshDefender();
  };
  H('defNo').onclick = closeModal;
}


/* ---------- NVIDIA Profile page ---------- */
const NV_LOGO = '<svg viewBox="0 0 48 48" width="34" height="34" fill="#fff">' +
  '<path d="M18 15c-6 .6-10 4.6-11.4 9 2.8 5.4 8.4 8.4 15 8 8-.5 14-5.2 17.4-11.6C34.4 13.7 27 10 18 15zm4.6 4.3c4.7 0 8.4 3.2 8.4 7.2s-3.7 7.3-8.4 7.3c-1.2 0-2.3-.2-3.3-.6 2.6-.3 4.5-2.1 4.5-4.4 0-2.5-2.3-4.5-5.1-4.5-.8 0-1.5.1-2.1.4 1.5-3 4.4-5.4 8-4.8z"/></svg>';

async function pageNvProfile() {
  pageShell('NVIDIA Profile', {crumb: 'System › NVIDIA Profile',
    text: 'One-tap NVIDIA driver profile — the same tuned global settings, applied for anyone.'},
    `<div id="nvWrap" style="position:relative">
     <div class="card" id="nvCard">
       <div class="row" style="align-items:center;gap:16px">
         <div class="nvlogo">${NV_LOGO}</div>
         <div style="flex:1">
           <b style="font-size:17px">NVIDIA Profile</b>
           <p id="nvState" style="color:var(--muted);font-size:12.5px;margin-top:5px">Checking...</p>
         </div>
         <button type="button" class="sw" id="nvTgl" role="switch" aria-label="NVIDIA Profile" aria-checked="false" disabled></button>
       </div>
       <div id="nvSetup" style="margin-top:14px"></div>
       <p style="color:var(--muted);font-size:11.5px;line-height:1.6;margin-top:16px">
         Only changes NVIDIA driver settings — nothing else on the PC. The first
         time you run this on a PC, it quietly saves that PC's current NVIDIA
         settings once, so turning the profile off puts them back exactly as they were.</p>
     </div>
     <div class="card nvsettings" id="nvSettings" style="margin-top:15px">
       <h3>What this profile applies</h3>
       <div id="nvSettingsList" style="color:var(--muted);font-size:12.5px">Loading...</div>
     </div>
     <div id="nvBlock" hidden></div>
     </div>`);
  await refreshNvProfile();
  loadNvSettings();
}

async function refreshNvProfile() {
  const st = await api('nvprofile_status');
  if (!st) return;
  window.__nv = st;
  // No NVIDIA GPU: seal the whole page behind a block the user can't click
  // off. They can still switch tabs (the sidebar is outside this overlay).
  const block = H('nvBlock');
  if (block) {
    if (st.nvidia === false) {
      block.hidden = false;
      block.innerHTML =
        `<div class="nvblock-inner">
           <div class="nvlogo" style="opacity:.9;margin-bottom:14px">${NV_LOGO}</div>
           <h2 style="margin:0 0 8px;font-size:19px">This profile is for NVIDIA GPUs</h2>
           <p style="color:var(--muted);font-size:13px;line-height:1.65;max-width:430px">
             This PC's graphics are ${st.gpu_name ? '<b>' + st.gpu_name + '</b>'
               : 'an AMD / integrated GPU'}, not an NVIDIA card, so there is no NVIDIA
             driver profile to apply here. Everything else in the app works as normal —
             just pick another tab on the left.</p>
         </div>`;
      return;
    }
    block.hidden = true;
  }
  const tgl = H('nvTgl');
  const ready = st.tool && st.profile;
  if (tgl) {
    tgl.classList.toggle('on', !!st.applied);
    tgl.classList.toggle('warn', st.state === 'partial');
    tgl.classList.toggle('dis', !ready);
    tgl.disabled = !ready; tgl.setAttribute('aria-checked',String(!!st.applied));
  }
  const state = H('nvState');
  if (state) {
    if (!st.nvidia) { state.textContent = 'No NVIDIA GPU detected on this PC.'; state.style.color = 'var(--muted)'; }
    else if (!ready) { state.textContent = 'Needs one-time setup (below).'; state.style.color = 'var(--warn)'; }
    else if (st.state === 'partial') {
      // Something changed these settings outside this app.
      state.textContent = `Partly applied — ${st.matched} of ${st.total} settings match. `
                        + `Toggle on to reapply the full profile.`;
      state.style.color = 'var(--warn)';
    }
    else if (st.state === 'unknown' && !st.checked) {
      state.textContent = 'Checking your current NVIDIA settings...';
      state.style.color = 'var(--muted)';
    }
    else { state.textContent = st.applied ? 'Profile is applied.' : 'Using NVIDIA defaults.';
           state.style.color = st.applied ? 'var(--good)' : 'var(--muted)'; }
  }
  const setup = H('nvSetup');
  if (setup) {
    const miss = [];
    if (!st.tool) miss.push('NVIDIA Profile Inspector (<b>' + (st.tool_names ? st.tool_names[0] : 'nvidiaProfileInspector.exe') + '</b>)');
    if (!st.profile) miss.push('the profile file (<b>' + (st.profile_name || 'TechLoungeProfile.nip') + '</b>)');
    setup.innerHTML = (st.nvidia && miss.length) ?
      `<div style="padding:11px 13px;border-radius:10px;background:rgba(255,190,61,.1);
         border:1px solid rgba(255,190,61,.28);font-size:12px;line-height:1.6;color:var(--text)">
         Drop ${miss.join(' and ')} into this app's folder, then reopen.
         <div style="margin-top:8px">
           <button class="btn ghost" onclick="api('open_url','${st.releases_url}')">Get Profile Inspector</button>
         </div></div>` : '';
  }
  if (tgl) tgl.onclick = () => { if (ready) confirmNvProfile(!st.applied); };
}

function confirmNvProfile(want) {
  showModal(`<div class="modal-card">
      <h2 style="margin:0 0 8px;font-size:18px">${want ? 'Apply NVIDIA Profile?' : 'Restore NVIDIA defaults?'}</h2>
      <p style="color:var(--muted);font-size:12.5px;line-height:1.6;margin:0 0 14px">
        ${want ? 'Applies the tuned global 3D settings to your NVIDIA driver.'
               : ((window.__nv && window.__nv.backup)
                  ? 'Restores the NVIDIA settings this PC had before the profile was first applied.'
                  : 'Resets the NVIDIA global 3D settings back to defaults.')}</p>
      <div class="row" style="gap:10px">
        <button class="btn" id="nvYes">${want ? 'Apply' : 'Restore'}</button>
        <button class="btn ghost" id="nvNo">Cancel</button>
      </div></div>`);
  H('nvYes').onclick = async () => {
    closeModal();
    if (H('nvState')) { H('nvState').textContent = 'Applying...'; H('nvState').style.color = 'var(--muted)'; }
    const r = await api('nvprofile_set', want);
    if (r && !r.ok && H('nvState')) {
      H('nvState').textContent = r.message || 'Could not apply.';
      H('nvState').style.color = 'var(--warn)';
    }
    await refreshNvProfile();
    loadNvSettings();
  };
  H('nvNo').onclick = closeModal;
}


async function loadNvSettings() {
  const el = H('nvSettingsList');
  if (!el) return;
  // Served from the startup cache in the normal case, so this returns at once.
  const ready = await api('nvprofile_ready');
  if (!ready) el.textContent = 'Reading your current NVIDIA settings...';
  const rows = await api('nvprofile_settings');
  if (!rows || !rows.length) {
    el.textContent = 'Profile settings unavailable.';
    return;
  }
  const hasCurrent = rows.some(r => r.current != null);
  el.innerHTML =
    (hasCurrent ? `<div class="nvhead"><span class="nvname"></span>
       <span class="nvcur">Current</span><span class="nvarrow"></span>
       <span class="nvval">After applying</span></div>` : '') +
    rows.map(r => {
      const changed = r.current != null && r.current !== r.target;
      return `<div class="nvrow">
         <span class="nvname">${r.name}</span>
         ${r.current != null
            ? `<span class="nvcur ${changed ? 'chg' : ''}">${r.current}</span>
               <span class="nvarrow">${svg('arrow')}</span>`
            : `<span class="nvcur"></span><span class="nvarrow">sets to</span>`}
         <span class="nvval">${r.target}</span>
       </div>`;
    }).join('');
}
