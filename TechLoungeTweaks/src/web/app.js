'use strict';

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
  // A call can land while the bridge is still being injected. Wait it out
  // instead of failing - this is what caused the "Bridge not ready" flash.
  if (!bridgeReady() && !USE_DEMO) await waitForBridge(IN_APP ? 20000 : 1200);
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
  fatal(name);
  return null;
}

// Hard stop. Shown instead of the UI when the Python backend is unreachable,
// so nobody is ever looking at numbers that did not come from their machine.
function fatal(what) {
  if (document.getElementById('fatal')) return;
  document.body.classList.remove('booting');
  const el = document.createElement('div');
  el.id = 'fatal';
  el.innerHTML =
    '<div class="fatal-card">' +
    '<h1>Cannot read this machine</h1>' +
    '<p>The app started but its system backend did not respond, so it has ' +
    'nothing real to show you. Nothing has been changed on this PC.</p>' +
    '<p class="fatal-why">This is not something you did wrong, and it is not ' +
    'a problem with your PC settings.</p>' +
    '<ol>' +
    '<li>Close the app completely and open it again - this clears it most times</li>' +
    '<li>If it keeps happening, reboot and try once more</li>' +
    '<li>Still failing? Send <b>TL-api.log</b> from this app\'s folder - ' +
    'it records exactly which step failed</li>' +
    '</ol>' +
    '<p class="fatal-code">failed call: ' + what + '</p>' +
    '</div>';
  document.body.appendChild(el);
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
  folder:'<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
  disk:'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 8h.01"/>',
  wrench:'<path d="M15 3a6 6 0 0 0-5.5 8.4L3 18v3h3l6.6-6.5A6 6 0 1 0 15 3"/>',
  driver:'<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M7 19v2h10v-2"/>',
  restore:'<path d="M3 12a9 9 0 1 0 3-6.7M3 4v5h5"/>'
};
const svg = k => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
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
  ['page','Drivers','driver'], ['page','Resources','wrench'],
  ['sec','TOOLS'],
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
    'Drivers': pageDrivers, 'Resources': pageRes,
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
  await api('bulk', STATE.page, on);
  items.forEach(t => t.applied = on);
  renderTweaks(STATE.page); refreshCounts();
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
  const info = await api('init');
  if (info) {
    STATE.tweaks = info.tweaks; STATE.cats = info.categories;
    STATE.admin = info.admin;
    document.getElementById('footAdmin').textContent =
      info.admin ? 'Administrator' : 'Not elevated';
    document.getElementById('footAdmin').style.color =
      info.admin ? 'var(--good)' : 'var(--warn)';
    renderSpecs(info.specs || {});
  }
  buildNav(); show('Home'); refreshCounts(); wireTips();
  buildQuick();
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
  if (!bridgeReady()) {
    document.body.classList.add('booting');
    // In the app, wait as long as it takes (WebView2 cold start can be slow).
    // In a browser there is no bridge coming, so bail quickly to demo data.
    const ok = await waitForBridge(IN_APP ? 20000 : 1200);
    document.body.classList.remove('booting');
    if (!ok) {
      if (DEMO_ALLOWED) {
        USE_DEMO = true;
      } else {
        fatal('init');
        return;          // never render anything rather than render fiction
      }
    }
  }
  boot();
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
  if (hadNone) buildQuick();
  if (STATE.cats.includes(STATE.page)) renderTweaks(STATE.page);
  if (STATE.page === 'Home') show('Home');
  if (STATE.page === 'Networking') pageNetworking();
};
window.py_specs = d => renderSpecs(d);

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
    const up = g.latest && g.latest === g.installed;
    return `<div class="card" style="margin-bottom:11px">
      <div class="row"><b style="font-size:15px">${g.name}</b>
      <div class="spacer"></div>
      <span class="badge ${up ? 'on' : (g.latest ? '' : '')}"
        style="${g.latest && !up ? 'background:rgba(255,190,61,.14);color:var(--warn)' : ''}">
        ${up ? 'UP TO DATE' : (g.latest ? 'UPDATE AVAILABLE' : 'NOT CHECKED')}</span></div>
      <div class="row" style="margin-top:14px;gap:34px">
        <div><div class="label">INSTALLED</div>
          <div style="font-size:19px;font-family:ui-monospace,Consolas,monospace">${g.installed}</div></div>
        ${g.latest ? `<div><div class="label">LATEST</div>
          <div style="font-size:19px;font-family:ui-monospace,Consolas,monospace;
            color:${up ? 'var(--good)' : 'var(--warn)'}">${g.latest}</div></div>` : ''}
      </div>
      <div class="row" style="margin-top:15px">
        ${g.latest && !up ? `<button class="btn" data-dl="${i}">Download Driver</button>` : ''}
        <button class="btn ghost" onclick="api('open_url','${g.page}')">Open vendor page</button>
        <span id="dlp${i}" style="color:var(--muted);font-size:11.5px"></span></div>
    </div>`;
  }).join('');
  document.querySelectorAll('[data-dl]').forEach(b => b.onclick = async () => {
    const g = d.gpus[+b.dataset.dl];
    b.disabled = true; b.textContent = 'Downloading…';
    const r = await api('download_driver', g.url, g.vendor);
    b.disabled = false; b.textContent = 'Download Driver';
    H('dlp' + b.dataset.dl).textContent =
      r && r.ok ? 'Saved to Downloads' : 'Failed: ' + (r && r.error || '');
  });
}
window.py_dlprogress = d => {
  const el = document.querySelector('[id^=dlp]');
  if (el) el.textContent = Math.round(d.frac * 100) + '%';
};

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
      <div id="verdict_${k}" style="margin-top:10px"></div>
      <div class="row" style="margin-top:12px">
        <button class="btn" data-res="${k}">Run</button>
        <button class="btn ghost" data-cancel="${k}" style="display:none">Cancel</button></div></div>`).join(''));
  document.querySelectorAll('[data-cancel]').forEach(b =>
    b.onclick = () => api('cancel_task', b.dataset.cancel));
  document.querySelectorAll('[data-res]').forEach(b => b.onclick = async () => {
    const k = b.dataset.res;
    const cx = document.querySelector(`[data-cancel="${k}"]`);
    b.disabled = true; b.textContent = 'Running…';
    if (cx) cx.style.display = '';
    H('verdict_' + k).innerHTML = '';
    const r = await api('resource_task', k);
    b.disabled = false; b.textContent = 'Run';
    if (cx) cx.style.display = 'none';
    H('res_' + k).textContent = '';
    const st = (r && r.state) || 'problem';
    const look = {
      clean:   ['✓', 'var(--good)', 'rgba(61,220,151,.13)'],
      fixed:   ['✓', 'var(--good)', 'rgba(61,220,151,.13)'],
      problem: ['!', 'var(--bad)',  'rgba(255,93,108,.13)'],
      cancelled:['—','var(--muted)','rgba(255,255,255,.06)'],
      busy:    ['—','var(--warn)', 'rgba(255,190,61,.13)'],
    }[st] || ['!', 'var(--bad)', 'rgba(255,93,108,.13)'];
    H('verdict_' + k).innerHTML =
      `<div style="display:flex;gap:10px;align-items:flex-start;padding:12px 14px;
        border-radius:12px;background:${look[2]};color:${look[1]};font-size:12.5px;
        line-height:1.55"><b style="font-size:14px">${look[0]}</b>
        <span>${(r && r.message) || 'Finished.'}</span></div>`;
  });
}
window.py_resline = d => {
  const el = H('res_' + d.key); if (el) el.textContent = d.text;
};

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
             <i id="gradeBar" style="width:50%;background:linear-gradient(90deg,#e0338f,#2f9db5)"></i></div></div></div>
         <p id="verdict" style="color:var(--muted);font-size:12px;margin-top:12px">Run a test to measure your connection.</p></div>
       <div class="card"><div class="label">INTERNET SPEED <span class="info" ${tipAttr('speed')}>?</span></div>
         <div style="margin-top:14px"><div class="row"><span style="color:var(--muted);font-size:11.5px">Download</span>
           <div class="spacer"></div><b id="dl" style="font-size:18px">—</b></div>
           <div class="bar"><i id="dlBar"></i></div></div>
         <div style="margin-top:14px"><div class="row"><span style="color:var(--muted);font-size:11.5px">Upload</span>
           <div class="spacer"></div><b id="ul" style="font-size:18px">—</b></div>
           <div class="bar"><i id="ulBar" style="background:linear-gradient(90deg,#7b5cff,#2fd4e8)"></i></div></div></div>
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
