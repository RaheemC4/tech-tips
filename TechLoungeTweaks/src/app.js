'use strict';

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
  document.documentElement.setAttribute('data-theme', name);
  try { localStorage.setItem('tl-theme', name); } catch (e) {}
  const pop = document.getElementById('themepop');
  if (pop) pop.querySelectorAll('.tsw').forEach(sw =>
    sw.classList.toggle('active', sw.dataset.theme === name));
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
    pop.innerHTML = THEMES.map(t =>
      `<div class="tsw" data-theme="${t[0]}" title="${t[0]}"
        style="background:linear-gradient(135deg,${t[1]},${t[2]})"></div>`).join('');
    document.body.appendChild(pop);
    pop.querySelectorAll('.tsw').forEach(sw =>
      sw.onclick = () => { applyTheme(sw.dataset.theme); pop.classList.remove('show');
                           btn.classList.remove('open'); });
  }
  const place = () => {
    // Hang it off the button itself so it stays put when the window resizes.
    const r = btn.getBoundingClientRect();
    pop.style.top = (r.bottom + 6) + 'px';
    pop.style.right = Math.max(8, window.innerWidth - r.right - 12) + 'px';
  };
  btn.onclick = e => {
    e.stopPropagation();
    const open = pop.classList.toggle('show');
    btn.classList.toggle('open', open);
    if (open) place();
    applyTheme(currentTheme());
  };
  window.addEventListener('resize', () => { if (pop.classList.contains('show')) place(); });
  document.addEventListener('click', e => {
    // e.target is the SVG path when the icon itself is clicked, so match the
    // button by closest() rather than identity.
    if (pop.classList.contains('show') && !pop.contains(e.target) &&
        !(e.target.closest && e.target.closest('#themebtn'))) {
      pop.classList.remove('show');
      btn.classList.remove('open');
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
const svg = k => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
  stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${ICONS[k]||ICONS.cpu}</svg>`;

let STATE = { tweaks: [], cats: [], page: 'Home', specs: {}, admin: true, snapshot: null };

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
  ['page','Virtual Machines','box'],
  ['page','Install Apps','box'],
  ['page','Boot Optimizer','bolt'], ['page','BIOS Info','cpu'],
  ['page','System Restore','restore']
];

function buildNav() {
  const el = document.getElementById('navlist');
  el.innerHTML = NAV.map(n => {
    if (n[0] === 'sec') return `<div class="navsec">${n[1]}</div>`;
    const chip = n[0] === 'cat' ? `<span class="chip" data-chip="${n[1]}">0/0</span>` : '';
    return `<div class="nav" data-nav="${n[1]}">${svg(n[2])}<span>${n[1]}</span>${chip}</div>`;
  }).join('');
  el.querySelectorAll('[data-nav]').forEach(n =>
    n.onclick = () => show(n.dataset.nav));
}

function show(name) {
  STATE.page = name;
  document.querySelectorAll('[data-nav]').forEach(n =>
    n.classList.toggle('active', n.dataset.nav === name));
  const isCat = STATE.cats.includes(name);
  const routes = {
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
  if (sw) sw.classList.toggle('on', !!t.applied);
  const badge = card.querySelector('.badge');
  if (badge) {
    badge.textContent = t.applied ? 'APPLIED' : 'NOT APPLIED';
    badge.className = 'badge' + (t.applied ? ' on' : '');
  }
}

function setToggle(key) {
  const t = STATE.tweaks.find(x => x.key === key);
  if (!t) return;
  const want = !t.applied;
  t.applied = want;            // optimistic
  paintCard(t);
  updateCounts();

  const run = () => api('toggle', key, want).then(r => {
    if (r && r.ok === false) {
      t.applied = (r.applied !== undefined) ? r.applied : !want;
      paintCard(t); updateCounts();
      if (r.message) banner(t.name + ': ' + r.message);
    }
  });
  INFLIGHT[key] = (INFLIGHT[key] || Promise.resolve()).then(run, run);
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
      <div class="foot">
        <span class="badge ${t.applied ? 'on' : ''}">
          ${t.applied ? 'APPLIED' : 'NOT APPLIED'}</span>
        <div class="sw ${t.applied ? 'on' : ''}" data-sw="${t.key}"></div>
      </div>
      ${t.warning ? `<div class="warnpill">▲ ${t.warning}</div>` : ''}
    </div>`).join('');

  document.querySelectorAll('[data-sw]').forEach(sw => {
    sw.onclick = () => setToggle(sw.dataset.sw);
  });
  wireTips();
}

async function applyAll(on) {
  const items = STATE.tweaks.filter(t => t.category === STATE.page);
  items.forEach(t => t.applied = on);      // flip first, write behind
  renderTweaks(STATE.page); refreshCounts();
  await api('bulk', STATE.page, on);
}

/* ---------- dashboard one-click setup ---------- */
// Tweaks "Apply recommended" leaves off - kept in sync with the server's
// RECOMMENDED_SKIP: the two risky ones plus GameDVR and Fullscreen Optimizations.
const RECOMMENDED_SKIP = ['mem_integrity', 'mitigations', 'gamedvr', 'fse'];

function wireBulk() {
  document.querySelectorAll('[data-bulk]').forEach(b => {
    b.onclick = () => runBulk(b.dataset.bulk);
  });
}

function bulkTargets(mode) {
  if (mode === 'all') return () => true;
  if (mode === 'recommended') return t => !RECOMMENDED_SKIP.includes(t.key);
  if (mode === 'defaults') return () => false;
  if (mode === 'revert') {
    const snap = STATE.snapshot || {};
    return t => !!snap[t.key];
  }
  return () => false;
}

let BULK_BUSY = false;
async function runBulk(mode) {
  if (BULK_BUSY) return;
  BULK_BUSY = true;
  const btns = document.querySelectorAll('[data-bulk]');
  btns.forEach(b => b.disabled = true);
  const status = H('bulkStatus');

  // 1) Flip every affected toggle immediately so the UI never looks frozen.
  const want = bulkTargets(mode);
  STATE.tweaks.forEach(t => { t.applied = want(t); });
  refreshCounts();
  if (STATE.cats.includes(STATE.page)) renderTweaks(STATE.page);

  const setStatus = (txt, spin) => {
    if (!status) return;
    status.hidden = false;
    status.innerHTML = (spin ? '<span class="spin"></span>' : '') +
      '<span>' + txt + '</span>';
  };
  const LABEL = {all: 'Applying every tweak', recommended: 'Applying the recommended tweaks',
                 revert: 'Reverting to how the PC was', defaults: 'Restoring Windows defaults'}[mode];
  setStatus(LABEL + '…', true);

  // 2) Write the tweaks.
  const r = await api('bulk_tweaks', mode);
  if (r && r.applied) {
    STATE.tweaks.forEach(t => {
      if (t.key in r.applied) t.applied = r.applied[t.key];
    });
    refreshCounts();
    if (STATE.cats.includes(STATE.page)) renderTweaks(STATE.page);
  }

  // 3) Defender + NVIDIA, per mode.
  const extras = [];
  const wantDefenderOff = (mode === 'all' || mode === 'recommended');
  const wantDefenderOn  = (mode === 'defaults');
  const wantNvidiaOn    = (mode === 'all' || mode === 'recommended');
  const wantNvidiaOff   = (mode === 'defaults' || mode === 'revert');

  // Only touch NVIDIA when this PC actually has an NVIDIA GPU + the tool.
  let nv = null;
  try { nv = await api('nvprofile_status'); } catch (e) {}
  const nvUsable = nv && nv.nvidia && nv.tool && nv.profile;

  if (wantNvidiaOn && nvUsable) {
    setStatus(LABEL + ' — applying NVIDIA profile…', true);
    const nr = await api('nvprofile_set', true);
    extras.push(nr && nr.ok !== false ? 'NVIDIA profile applied'
                                      : 'NVIDIA profile could not apply');
  } else if (wantNvidiaOn && nv && !nv.nvidia) {
    extras.push('No NVIDIA GPU — profile skipped');
  } else if (wantNvidiaOff && nvUsable) {
    setStatus(LABEL + ' — restoring NVIDIA settings…', true);
    await api('nvprofile_set', false);
    extras.push('NVIDIA settings restored');
  }

  if (wantDefenderOff || wantDefenderOn) {
    setStatus(LABEL + ' — ' + (wantDefenderOff ? 'turning Defender off' : 'turning Defender on') + '…', true);
    const dr = await api('defender_set', wantDefenderOn);
    if (dr && dr.tamper && wantDefenderOff)
      extras.push('Defender needs one manual step — open the Defender tab to finish');
    else
      extras.push(wantDefenderOff ? 'Defender turned off' : 'Defender turned on');
  }

  // Virtualisation: the apply modes and Windows Defaults are all gaming-facing,
  // so put the machine in the gaming/protected state. Revert All is left alone
  // because we did not record which mode the PC was in beforehand.
  if (mode === 'all' || mode === 'recommended' || mode === 'defaults') {
    try {
      const vs = await api('virt_status');
      if (vs && vs.mode !== 'gaming') {
        setStatus(LABEL + ' — setting up for gaming…', true);
        const vr = await api('virt_set', 'gaming');
        if (vr && vr.ok) extras.push('Set up for gaming, Memory Integrity off (restart needed)');
      }
    } catch (e) {}
  }

  const done = {all: 'Applied everything.', recommended: 'Recommended tweaks applied.',
                revert: 'Reverted to your original setup.', defaults: 'Windows defaults restored.'}[mode];
  setStatus(done + (extras.length ? '  •  ' + extras.join('  •  ') : ''), false);

  btns.forEach(b => b.disabled = false);
  BULK_BUSY = false;
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
    return `<div class="card" onclick="show('${c.replace(/'/g, "\\'")}')" style="cursor:pointer;padding:15px">
      <div class="row"><span style="font-size:12.5px;font-weight:620">${c}</span>
      <div class="spacer"></div><span style="font-size:11px;color:${on ? 'var(--good)' : 'var(--faint)'}">${on}/${items.length}</span></div>
      <div class="bar"><i style="width:${p}%"></i></div></div>`;
  }).join('');
}

function animateNum(el, to) {
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
  const acts = [['Create Restore Point','System Restore'],
                ['Run Boot Optimizer','Boot Optimizer'],
                ['Test Connection','Networking'],
                ['Clean Up Disk','Disk Cleanup'],
                ['Check Drivers','Drivers']];
  document.getElementById('quickRow').innerHTML = acts.map(
    ([l, t]) => `<button class="btn ghost" onclick="show('${t}')">${l}</button>`).join('');
}

function renderSpecs(s) {
  if (!s || typeof s !== 'object') return;
  document.getElementById('specs').innerHTML = Object.entries(s).map(
    ([k, v]) => `<div class="specrow"><span class="k">${k}</span><span class="v">${v}</span></div>`).join('');
}

/* ---------- tooltips ---------- */
const tip = document.getElementById('tip');
function wireTips() {
  document.querySelectorAll('.info[data-t]').forEach(el => {
    el.onmouseenter = () => {
      const [t, b, g] = el.dataset.t.split('|');
      tip.innerHTML = `<b>${t}</b><p>${b}</p>${g ? `<div class="good">${g}</div>` : ''}`;
      const r = el.getBoundingClientRect();
      tip.classList.add('show');
      const tw = tip.offsetWidth, th = tip.offsetHeight;
      tip.style.left = Math.min(r.left, innerWidth - tw - 14) + 'px';
      tip.style.top = (r.bottom + th + 14 > innerHeight ? r.top - th - 10 : r.bottom + 10) + 'px';
    };
    el.onmouseleave = () => tip.classList.remove('show');
  });
}

/* ---------- cursor reactivity ---------- */
const spot = document.getElementById('spot');
addEventListener('mousemove', e => {
  // Mid-drag the window itself is moving; chasing the cursor here would
  // repaint the whole backdrop every frame. Leave it exactly where it is.
  if (document.body.classList.contains('dragging')) return;
  spot.style.opacity = '1';
  spot.style.left = e.clientX + 'px';
  spot.style.top = e.clientY + 'px';
  const c = e.target.closest('.card');
  if (c) {
    const r = c.getBoundingClientRect();
    c.style.setProperty('--mx', (e.clientX - r.left) + 'px');
    c.style.setProperty('--my', (e.clientY - r.top) + 'px');
  }
});

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
  document.body.classList.remove('booting');
  document.body.classList.remove('booting-slow');
  if (info) {
    STATE.tweaks = info.tweaks; STATE.cats = info.categories;
    STATE.admin = info.admin;
    document.getElementById('footAdmin').textContent =
      info.admin ? 'Administrator' : 'Not elevated';
    document.getElementById('footAdmin').style.color =
      info.admin ? 'var(--good)' : 'var(--warn)';
    renderSpecs(info.specs || {});
  }
  buildNav(); show('Home'); refreshCounts(); wireTips(); wireTheme();
  buildQuick(); wireBulk();
  if (info && info.scanning) {
    H('scoreNote').textContent = 'Checking what is already applied…';
    renderSpecs({ Status: 'Reading hardware…' });
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
  // wait for it indefinitely behind a calm "Starting…" splash and NEVER show
  // an error for slowness. The only job here is to look patient, not broken.
  document.body.classList.add('booting');
  const t0 = Date.now();
  (function poll() {
    if (bridgeReady()) {
      document.body.classList.remove('booting');
      document.body.classList.remove('booting-slow');
      boot();
      return;
    }
    // After a while, reassure rather than alarm - still no error.
    if (Date.now() - t0 > 20000) document.body.classList.add('booting-slow');
    setTimeout(poll, 40);
  })();
  window.addEventListener('pywebviewready', () => {
    if (bridgeReady() && !window.__booted) {
      document.body.classList.remove('booting');
      document.body.classList.remove('booting-slow');
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
  // First real scan defines the "how it was" baseline for Revert All.
  if (!STATE.snapshot)
    STATE.snapshot = Object.fromEntries(d.tweaks.map(t => [t.key, !!t.applied]));

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
     <div class="grid g3" id="sysBody"><div class="card">Reading…</div></div>`);
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
  H('sysBody').innerHTML = '<div class="card">Reading…</div>';
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
async function pageClean() {
  pageShell('Disk Cleanup', {crumb:'System › Disk Cleanup',
    text:'Find and remove junk that is safe to delete.'},
    `<div class="card" style="margin-bottom:15px">
       <div class="row"><h3 id="cleanTotal" style="font-size:21px">Scanning…</h3>
       <div class="spacer"></div>
       <button class="btn ghost" onclick="pageClean()">Rescan</button>
       <button class="btn" onclick="runClean()">Clean Up</button></div>
       <div class="bar" style="height:9px"><i id="diskBar"></i></div>
       <p id="diskLbl" style="color:var(--muted);font-size:11.5px;margin-top:8px"></p>
       <p id="freedLbl" style="color:var(--good);font-size:12px;margin-top:5px;font-weight:600"></p>
     </div>
     <div id="cleanList"></div>
     <div class="card" id="cleanLog" style="display:none;margin-top:14px;
       font-family:ui-monospace,Consolas,monospace;font-size:11.5px;color:var(--muted);
       max-height:190px;overflow:auto;white-space:pre-wrap"></div>`);
  const d = await api('clean_scan');
  if (!d) return;
  CLEAN = d.items;
  H('diskBar').style.width = (d.disk.used / d.disk.total * 100) + '%';
  H('diskLbl').textContent =
    `Drive C:  ${d.disk.usedH} of ${d.disk.totalH} used  ·  ${d.disk.freeH} free`;
  renderClean();
}
function renderClean() {
  H('cleanList').innerHTML = CLEAN.map((it, i) => `
    <div class="card" style="margin-bottom:10px;padding:15px">
      <div class="row">
        <input type="checkbox" ${it.default && it.bytes ? 'checked' : ''}
          ${it.bytes ? '' : 'disabled'} data-cl="${i}"
          style="width:17px;height:17px;accent-color:var(--accent);cursor:pointer">
        <b style="font-size:13px">${it.name}</b>
        <div class="spacer"></div>
        <b style="color:${it.bytes ? 'var(--good)' : 'var(--faint)'}">${it.human}</b>
      </div>
      <p style="color:var(--muted);font-size:11.5px;margin:8px 0 0 29px">
        ${it.desc}${it.files ? '   ·   ' + it.files.toLocaleString() + ' files' : ''}</p>
    </div>`).join('');
  document.querySelectorAll('[data-cl]').forEach(c => c.onchange = recalcClean);
  recalcClean();
}
function recalcClean() {
  let t = 0;
  document.querySelectorAll('[data-cl]').forEach(c => {
    if (c.checked) t += CLEAN[+c.dataset.cl].bytes; });
  H('cleanTotal').textContent = human(t) + ' can be freed';
}
function human(n) {
  const u = ['B','KB','MB','GB','TB']; let i = 0;
  while (n >= 1024 && i < 4) { n /= 1024; i++; }
  return (i < 2 ? Math.round(n) : n.toFixed(1)) + ' ' + u[i];
}
window.py_cleanlog = d => {
  const el = H('cleanLog'); if (!el) return;
  el.style.display = 'block';
  el.textContent += `${d.name}: freed ${d.freed}${d.skipped ? `, ${d.skipped} in use` : ''}\n`;
  el.scrollTop = el.scrollHeight;
};
async function runClean() {
  const sel = [];
  document.querySelectorAll('[data-cl]').forEach(c => {
    if (c.checked) sel.push(CLEAN[+c.dataset.cl]); });
  if (!sel.length) return;
  H('cleanLog').style.display = 'block';
  H('cleanLog').textContent = '--- Cleaning ---\n';
  const r = await api('clean_run', sel);
  if (r) H('freedLbl').textContent =
    `Freed ${r.freed}${r.skipped ? `  ·  ${r.skipped} file(s) locked by a running app` : ''}`;
  setTimeout(pageClean, 1200);
}

/* ---------------- Drivers ---------------- */
async function pageDrivers() {
  pageShell('Graphics Drivers', {crumb:'System › Drivers',
    text:'Checked live against the vendor every time you open this page.'},
    `<div class="row" style="margin-bottom:15px">
      <button class="btn" onclick="pageDrivers()">Check for Updates</button>
      <span id="drvStatus" style="color:var(--muted);font-size:12px"></span></div>
     <div id="drvList"><div class="card">Querying vendor…</div></div>
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
        H('dlp' + i).textContent = job.line || 'Downloading…';
      } else if (job && job.result) {
        const r = job.result;
        H('dlp' + i).textContent = r.ok ? 'Saved to Downloads'
          : (r.cancelled ? 'Cancelled' : 'Failed: ' + (r.error || ''));
      }
    };
    JOB_RENDERERS[jobkey] = paint;
    if (JOBS[jobkey]) paint(JOBS[jobkey]);

    b.onclick = async () => {
      paint({state: 'running', progress: 0, line: 'Starting…'});
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
    text:'Repair tools for a misbehaving Windows.'},
    RES.map(([k, t, d]) => `<div class="card" style="margin-bottom:11px">
      <b style="font-size:15px">${t}</b>
      <p style="color:var(--muted);font-size:12px;margin-top:6px;line-height:1.6">${d}</p>
      <div id="res_${k}" style="color:var(--muted);font-size:11.5px;margin-top:10px"></div>
      <div id="prog_${k}" class="jobbar" style="display:none"><i></i></div>
      <div id="verdict_${k}" style="margin-top:10px"></div>
      <div class="row" style="margin-top:12px">
        <button class="btn" data-res="${k}">Run</button>
        <button class="btn ghost" data-cancel="${k}" style="display:none">Cancel</button></div></div>`).join(''));

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
        H('res_' + k).textContent = pctTxt + (job.line || 'Working…') + time;
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
      paint({state: 'running', line: 'Starting…'});
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
    `<div id="virtBody"><div class="card">Reading virtualisation state…</div></div>`);
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
    ${!st.vt_firmware ? `<div class="card" style="margin-bottom:14px;
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
    if (wrap) { wrap.hidden = false; H('virtMsg').textContent = 'Applying…'; }
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

async function pageApps() {
  pageShell('Install Apps', {crumb: 'Tools › Install Apps',
    text: 'Runtimes, browsers and game clients, installed silently from the vendor.'},
    `<div id="appsBody"><div class="card">Loading the catalogue…</div></div>`);
  const cat = APPCACHE || await api('app_catalog');
  if (!cat) return;
  APPCACHE = cat;

  const groups = cat.groups.map(g => {
    const items = cat.apps.filter(a => a.group === g);
    if (!items.length) return '';
    return `<div class="section">${g}</div>
      <div class="grid g2">${items.map(a => `
        <div class="card appcard" data-app="${a.id}">
          <div class="row" style="align-items:flex-start;gap:12px">
            <div style="flex:1">
              <b style="font-size:14.5px">${a.name}</b>
              <p style="color:var(--muted);font-size:11.5px;line-height:1.55;margin-top:5px">${a.desc}</p>
            </div>
            <span class="badge" title="${a.route === 'winget'
              ? 'Installed through the Windows Package Manager'
              : (a.route === 'direct' ? 'Downloaded straight from the vendor'
                                      : 'No automatic route - opens the vendor page')}"
              >${a.route === 'winget' ? 'WINGET' : (a.route === 'direct' ? 'DIRECT' : 'MANUAL')}</span>
          </div>
          <div id="appline_${a.id}" style="color:var(--muted);font-size:11.5px;margin-top:9px"></div>
          <div class="jobbar" id="appbar_${a.id}" style="display:none"><i></i></div>
          <div id="appres_${a.id}" style="margin-top:8px"></div>
          <div class="row" style="margin-top:11px;gap:9px">
            ${a.installable ? `<button class="btn" data-inst="${a.id}">Install</button>` : ''}
            <button class="btn ghost" data-cancelapp="${a.id}" style="display:none">Cancel</button>
            <button class="btn ghost" onclick="api('open_url','${a.page}')">Vendor page</button>
          </div>
        </div>`).join('')}</div>`;
  }).join('');

  H('appsBody').innerHTML = `
    ${cat.winget ? '' : `<div class="card" style="margin-bottom:14px;
        border-color:rgba(255,190,61,.3);background:rgba(255,190,61,.08)">
        <b style="color:var(--warn);font-size:13px">Windows Package Manager is missing</b>
        <p style="color:var(--muted);font-size:12px;line-height:1.6;margin-top:6px">
          Debloated Windows images usually strip it out. Anything marked
          <b>DIRECT</b> still installs normally, straight from the vendor.
          Entries marked <b>MANUAL</b> need their vendor page.</p></div>`}
    ${storeCardHtml()}
    ${groups}
    <div class="card" style="margin-top:16px"><p style="color:var(--muted);font-size:11.5px;line-height:1.65">
      Downloads only ever come from each vendor's own domain — the app refuses
      any link that is not on that allowlist — and installers run with their
      official silent switches. Nothing is bundled with this app and nothing is
      repacked or modified.</p></div>`;

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
        H('appline_' + a.id).textContent = (job.line || 'Working…') + t;
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
      paint({state: 'running', progress: 0, line: 'Starting…'});
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
        <p id="storeState" style="color:var(--muted);font-size:12px;margin-top:5px">Checking…</p>
      </div>
    </div>
    <div class="row" style="margin-top:13px;gap:9px;flex-wrap:wrap">
      <button class="btn" id="storeOn">Install / restore</button>
      <button class="btn ghost" id="storeOff">Remove both</button>
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

  H('storeOn').onclick = async () => {
    H('storeMsg').textContent = 'Restoring…'; H('storeMsg').style.color = 'var(--muted)';
    const r = await api('store_set', 'both', true);
    paint(r && r.status);
    if (r && r.ok) { H('storeMsg').textContent = 'Done.'; H('storeMsg').style.color = 'var(--good)'; }
    else {
      H('storeMsg').textContent = (r && r.message) || 'Could not restore them.';
      H('storeMsg').style.color = 'var(--warn)';
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
      H('storeMsg').textContent = 'Removing…';
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
    `<div id="biosBody"><div class="card">Reading…</div></div>`);
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
    H('rpBtn').disabled = true; H('rpBtn').textContent = 'Creating…';
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
     <div class="grid" style="grid-template-columns:repeat(3,1fr);margin-bottom:15px">
       <div class="card"><div class="label">BUFFERBLOAT GRADE <span class="info" ${tipAttr('bloat')}>?</span></div>
         <div style="display:flex;align-items:center;gap:16px;margin-top:14px">
           <b id="grade" style="font-size:44px;color:var(--muted)">—</b>
           <div style="flex:1"><div class="bar" style="height:22px;border-radius:11px">
             <i id="gradeBar" style="width:50%;background:linear-gradient(90deg,var(--accent),var(--accent-2))"></i></div></div></div>
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
     <div class="card" style="margin-bottom:22px"><div class="label">YOUR CONNECTION <span class="info" ${tipAttr('conn')}>?</span></div>
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
}
function renderTweaksInto(items, cat) {
  const g = H('netTweakGrid'); if (!g) return;
  g.innerHTML = items.map(t => `
    <div class="card tweak ${t.applied ? 'on' : ''}" data-key="${t.key}">
      <div class="top"><div class="ico">${svg(t.icon || 'net')}</div><h3>${t.name}</h3></div>
      <div class="desc">${t.desc}</div>
      <div class="foot"><span class="badge ${t.applied ? 'on' : ''}">
        ${t.applied ? 'APPLIED' : 'NOT APPLIED'}</span>
        <div class="sw ${t.applied ? 'on' : ''}" data-sw="${t.key}"></div></div>
      ${t.warning ? `<div class="warnpill">▲ ${t.warning}</div>` : ''}</div>`).join('');
  document.querySelectorAll('[data-sw]').forEach(sw => {
    sw.onclick = () => setToggle(sw.dataset.sw);
  });
}
async function netBulk(on) {
  await api('bulk', 'Networking', on);
  STATE.tweaks.filter(t => t.category === 'Networking')
    .forEach(t => t.applied = on);
  pageNetworking(); refreshCounts();
}
const fmtSpeed = m => !m ? '—' : (m >= 1000 ? (m / 1000).toFixed(2) + ' Gbps' : Math.round(m) + ' Mbps');
window.py_netprogress = d => {
  if (H('netStatus')) H('netStatus').textContent = d.label + '…';
  if (H('netBar')) H('netBar').style.width = Math.min(100, d.frac * 100) + '%';
};
window.py_netpartial = d => paintNet(d.res, d.stage);
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
  H('netRun').disabled = true; H('netRun').textContent = 'Running…';
  ['lat0','lat1','lat2','dl','ul','jit'].forEach(i => { if (H(i)) H(i).textContent = '—'; });
  H('grade').textContent = '—';
  const r = await api('nettest');
  H('netRun').disabled = false; H('netRun').textContent = 'Run Test';
  if (!r || r.error) { H('netStatus').textContent = (r && r.error) || 'Test failed';
    H('netStatus').style.color = 'var(--warn)'; return; }
  paintNet(r, 'all');
  const ms = v => v ? Math.round(v) + ' ms' : '—';
  const j = r.idle_jitter, lj = r.jitter_ms;
  H('jit').textContent = (lj && j && lj > j * 1.5) ? `${Math.round(j)} / ${Math.round(lj)} ms` : ms(j);
  H('jit').style.color = j == null ? 'var(--text)' : (j < 5 ? 'var(--good)' : j < 20 ? 'var(--warn)' : 'var(--bad)');
  (r.activities || []).forEach(([n, ok], i) => {
    const el = H('cr' + i); if (!el) return;
    el.textContent = ok === null ? '?' : (ok ? '✓' : '✕');
    el.className = 'badge ' + (ok ? 'on' : '');
    if (ok === false) el.style.cssText = 'background:rgba(255,93,108,.14);color:var(--bad)';
  });
  const split = r.idle_ms && r.loaded_ms
    ? Math.max(8, Math.min(92, r.idle_ms / Math.max(r.loaded_ms, r.idle_ms * 1.2) * 100)) : 50;
  H('gradeBar').style.width = split + '%';
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
    api('maximize');
  });
})();


/* ---------- generic confirm modal ---------- */
function showModal(html) {
  let o = document.getElementById('modal');
  if (!o) { o = document.createElement('div'); o.id = 'modal';
            o.className = 'modal-overlay'; document.body.appendChild(o); }
  o.innerHTML = html; o.classList.add('show');
  o.onclick = e => { if (e.target === o) closeModal(); };
}
function closeModal() {
  const o = document.getElementById('modal');
  if (o) { o.classList.remove('show'); o.innerHTML = ''; }
}

/* ---------- Windows Defender page ---------- */
async function pageDefender() {
  pageShell('Windows Defender', {crumb: 'System › Defender',
    text: 'Turn Microsoft Defender fully on or off. Reads the live state from this PC.'},
    `<div class="card" id="defCard">
       <div class="row" style="align-items:flex-start">
         <div style="flex:1">
           <b style="font-size:16px">Microsoft Defender</b>
           <p id="defState" style="color:var(--muted);font-size:12.5px;margin-top:6px">Reading current state…</p>
         </div>
         <div class="sw" id="defTgl" role="switch"></div>
       </div>
       <div id="defTamper"></div>
       <div id="defList" style="margin-top:16px"></div>
       <p style="color:var(--muted);font-size:11.5px;line-height:1.6;margin-top:16px">
         Turning Defender off leaves this PC with no antivirus until you turn it
         back on. Only do this if you run something else or accept the risk.
         Everything here is undone by the same toggle.</p>
     </div>`);
  await refreshDefender();
}

async function refreshDefender() {
  const st = await api('defender_status');
  if (!st) return;
  window.__def = st;
  const tgl = H('defTgl');
  if (tgl) tgl.classList.toggle('on', !!st.active);
  const state = H('defState');
  if (state) {
    state.textContent = !st.present
      ? 'Defender is not installed on this PC — nothing to turn off.'
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
    if (H('defState')) { H('defState').textContent = 'Working…'; H('defState').style.color = 'var(--muted)'; }
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
           <p id="nvState" style="color:var(--muted);font-size:12.5px;margin-top:5px">Checking…</p>
         </div>
         <div class="sw" id="nvTgl" role="switch"></div>
       </div>
       <div id="nvSetup" style="margin-top:14px"></div>
       <p style="color:var(--muted);font-size:11.5px;line-height:1.6;margin-top:16px">
         Only changes NVIDIA driver settings — nothing else on the PC. The first
         time you run this on a PC, it quietly saves that PC's current NVIDIA
         settings once, so turning the profile off puts them back exactly as they were.</p>
     </div>
     <div class="card nvsettings" id="nvSettings" style="margin-top:15px">
       <h3>What this profile applies</h3>
       <div id="nvSettingsList" style="color:var(--muted);font-size:12.5px">Loading…</div>
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
      state.textContent = 'Checking your current NVIDIA settings…';
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
    if (H('nvState')) { H('nvState').textContent = 'Applying…'; H('nvState').style.color = 'var(--muted)'; }
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
  if (!ready) el.textContent = 'Reading your current NVIDIA settings…';
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
               <span class="nvarrow">→</span>`
            : `<span class="nvcur"></span><span class="nvarrow">sets to</span>`}
         <span class="nvval">${r.target}</span>
       </div>`;
    }).join('');
}
