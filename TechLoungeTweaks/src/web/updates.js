'use strict';
let updateTimer = null;
let updateLast = null;
const EXTRA_TOOLS = [
  {id:'driverbooster', name:'IObit Driver Booster', icon:'wrench', text:'Review drivers in Driver Booster. Choose driver changes inside the tool.'},
  {id:'treesize', name:'TreeSize Professional', icon:'folder', text:'Explore folder sizes and find what is using disk space.'},
  {id:'dlss', name:'DLSS Swapper', icon:'gpu', text:'Manage the upscaling libraries used by your games.'},
  {id:'bcu', name:'Bulk Crap Uninstaller', icon:'box', text:'Remove unwanted apps and review leftover files.'},
  {id:'nvpi', name:'NVIDIA Profile Inspector', icon:'nvidia', text:'Open the full Revamped interface to explore NVIDIA driver profiles.'},
  {id:'openmouse', name:'OpenMouse', icon:'wrench', text:'Configure supported mice in your default browser. Mouse access needs WebHID support.'}
];
const UPDATE_ICON = '<svg class="update-sync" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 7v5h-5M4 17v-5h5"/><path d="M6.1 6.1a8 8 0 0 1 13.2 3.1M4.7 14.8a8 8 0 0 0 13.2 3.1"/></svg>';

function startUpdateMonitor() {
  if (updateTimer || !window.pywebview) return;
  const poll = async () => {
    try {
      const state = await api('updates_status');
      if (state?.items) { updateLast = state; paintUpdates(state); }
    } finally { updateTimer = setTimeout(poll, updateLast?.busy ? 750 : 5000); }
  };
  updateTimer = setTimeout(poll, 1500);
}

function closeUpdates() {
  const panel = H('updatesPanel');
  if (panel) panel.hidden = true;
  H('updatesButton')?.setAttribute('aria-expanded', 'false');
}

async function openUpdates() {
  let panel = H('updatesPanel');
  if (!panel) {
    panel = document.createElement('aside');
    panel.id = 'updatesPanel'; panel.hidden = true;
    panel.setAttribute('role', 'dialog'); panel.setAttribute('aria-label', 'Updates');
    panel.innerHTML = `<header><div class="update-heading"><span class="update-emblem">${UPDATE_ICON}</span><div><div class="update-eyebrow">APP + TOOLS</div><h3>Updates</h3></div></div><button class="update-close" id="closeUpdates" aria-label="Close updates">×</button></header>
      <div class="update-summary"><i aria-hidden="true"></i><span id="updateSummary" role="status" aria-live="polite">Checking for updates…</span></div>
      <div class="update-body">
      <div id="updateAppRow"></div><div id="updateToolRows"></div>
      <div id="updateOperation" role="status" aria-live="polite" hidden><p id="updateStatus"></p><p id="updateProgress"></p>
        <button class="btn ghost" id="updateCancel" hidden>Cancel download</button></div>
      <button class="btn" id="updateRestart" hidden>Restart & apply</button>

      </div><footer><button class="update-check" id="updateCheck">${UPDATE_ICON}<span id="updateCheckLabel">Check for updates</span></button><span id="updateChecked"></span></footer>`;
    document.body.appendChild(panel);
    watchShellOverlay(panel);
    H('closeUpdates').onclick = () => { closeUpdates(); H('updatesButton').focus(); };
    H('updateCheck').onclick = () => updateAction('updates_check');
    H('updateCancel').onclick = () => updateAction('updates_cancel');
    H('updateRestart').onclick = () => updateAction('updates_restart');
  }
  panel.hidden = false;
  H('updatesButton')?.setAttribute('aria-expanded', 'true');
  if (updateLast) paintUpdates(updateLast);
  const state = await api('updates_status');
  if (state?.items) { updateLast = state; paintUpdates(state); }
}

document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && !H('modal')?.classList.contains('show')) closeUpdates();
});
document.addEventListener('pointerdown', e => {
  if (!e.target.closest('#updatesPanel, #updatesButton, #modal') && !H('modal')?.classList.contains('show')) closeUpdates();
});

let nvpiOpening = false;
let nvpiOpeningTimer = null;
function paintNvpiOpening() {
  document.querySelectorAll('[data-tool="nvpi"], [data-extra-tool="nvpi"]').forEach(button => {
    if (nvpiOpening) {
      if (!button.hasAttribute('data-launch-disabled')) button.dataset.launchDisabled = button.disabled ? '1' : '0';
      button.disabled = true;
    } else if (button.hasAttribute('data-launch-disabled')) {
      button.disabled = button.dataset.launchDisabled === '1';
      delete button.dataset.launchDisabled;
    }
    button.textContent = nvpiOpening ? 'Opening…' : 'Open';
    button.setAttribute('aria-busy', String(nvpiOpening));
  });
}
function setNvpiOpening(value) {
  nvpiOpening = value;
  clearTimeout(nvpiOpeningTimer);
  if (value) nvpiOpeningTimer = setTimeout(() => setNvpiOpening(false), 95000);
  paintNvpiOpening();
}
async function updateAction(method, key) {
  const openingNvpi = method === 'updates_launch' && key === 'nvpi';
  if (openingNvpi) {
    if (nvpiOpening) return;
    setNvpiOpening(true);
  }
  try {
  if (method === 'updates_restart' && !await confirmAction('Restart and apply?', 'TechLoungeTweaks will close, apply the downloaded update and reopen.', 'Restart')) return;
  const result = await api(method, ...(key === undefined ? [] : [key]));
  if (result?.ok === false) banner(result.message);
  if (method === 'updates_restart' && result?.ok) {
    banner('Restarting TechLoungeTweaks to apply the update…');
    return; // Do not start another bridge request during native shutdown.
  }
  if (openingNvpi && (!result || result.ok === false)) setNvpiOpening(false);
  const state = await api('updates_status');
  if (state?.items) { updateLast = state; paintUpdates(state); }
  if (method === 'updates_apply' && result?.ok) await openUpdates();
  } catch(error) {
    if (openingNvpi) setNvpiOpening(false);
    throw error;
  }
}

function versionLabels(item) {
  if (item.local) return `<div class="tool-versions"><span><span class="version-label">Included version</span><b>${textEscape(item.installed || 'Not installed')}</b></span></div><small>Personal bundled tool</small>`;
  const older = item.action === 'Update';
  const unavailable = item.check_error || item.status === 'unavailable';
  const latest = !unavailable && item.available && (item.id !== 'app' || /^v?\d+(?:\.\d+)*$/.test(item.available)) ? item.available : null;
  const format = value => {
    const match = item.id === 'app' && /^(\d{4}\.\d{2}\.\d{2})\.(\d{6})$/.exec(value || '');
    return match ? `${textEscape(match[1])}<em>Build ${match[2]}</em>` : textEscape(value || 'Unavailable');
  };
  return `<div class="tool-versions"><span><span class="version-label">Current</span><b title="${textEscape(item.installed || '')}" class="${older ? 'version-old' : ''}">${format(item.installed)}</b></span>
    <span><span class="version-label">Latest</span><b title="${textEscape(latest || '')}" class="${latest ? 'version-latest' : 'version-unknown'}">${latest ? format(latest) : unavailable ? 'Unavailable' : 'Checking…'}</b></span></div>
    ${older ? '<small class="version-old">Update available</small>' : ''}`;
}

function updateRow(item, busy) {
  return `<div class="update-row ${item.action === 'Update' ? 'update-needed' : ''}"><div class="update-row-info"><strong>${textEscape(item.name)}</strong>${versionLabels(item)}</div>
    <div class="update-actions">${item.launch ? `<button class="btn ghost" data-tool="${textEscape(item.id)}">Open</button>` : ''}
    ${item.rollback ? `<button class="update-rollback" data-rollback="${textEscape(item.id)}" ${busy ? 'disabled' : ''}>Previous version</button>` : ''}
    ${item.action ? `<button class="btn" data-update="${textEscape(item.id)}" ${busy ? 'disabled' : ''}>${item.id === 'app' ? 'Download' : textEscape(item.action)}</button>` : ''}</div></div>`;
}

function paintUpdates(state) {
  const rows = state.items || [];
  const app = rows.find(x => x.id === 'app');
  const tools = rows.filter(x => x.id !== 'app' && x.action === 'Update');
  const visibleTools = rows.filter(x => ['dlss','bcu','nvpi','driverbooster','treesize'].includes(x.id));
  const appAvailable = app?.action === 'Update';
  const pill = H('updatesButton');
  if (pill) {
    const label = state.ready ? 'Restart to update' : state.busy ? 'Downloading…' : !state.checking && appAvailable ? 'App update' : !state.checking && tools.length ? tools.length + (tools.length === 1 ? ' tool update' : ' tool updates') : 'Updates';
    H('updatesButtonLabel').textContent = label;
    const count = (appAvailable ? 1 : 0) + tools.length;
    H('updatesButtonCount').hidden = !count || state.checking || state.busy || !!state.ready;
    H('updatesButtonCount').textContent = count;
    pill.classList.toggle('has-update', !!state.ready || (!state.checking && (appAvailable || tools.length > 0)));
    pill.classList.toggle('is-checking', !!state.checking);
    pill.setAttribute('aria-label', label + '. Open update panel');
  }
  paintExtraTools(state);
  if (!H('updatesPanel')) return;
  H('updatesPanel').dataset.state = state.checking ? 'checking' : state.ready || appAvailable || tools.length ? 'available' : app?.status === 'current' ? 'current' : 'unavailable';
  H('updateSummary').textContent = state.checking ? 'Checking for updates…' : state.ready ? 'App update ready to apply' : appAvailable ? 'A new app version is available' : app?.status === 'current' ? 'App is up to date' : app?.status === 'unavailable' ? 'App version could not be checked' : 'Checking app version…';
  const appContent = JSON.stringify([app, state.busy, state.checking]);
  if (H('updateAppRow').dataset.content !== appContent) {
    H('updateAppRow').dataset.content = appContent;
    H('updateAppRow').innerHTML = app ? updateRow({...app, launch:false}, state.busy || state.checking) : '';
  }
  const toolContent = JSON.stringify([visibleTools, state.busy, state.checking]);
  if (H('updateToolRows').dataset.content !== toolContent) {
    H('updateToolRows').dataset.content = toolContent;
    H('updateToolRows').innerHTML = visibleTools.length ? '<div class="update-label">BUNDLED TOOLS</div>' + visibleTools.map(x => updateRow(x, state.busy || state.checking)).join('') : '';
  }
  H('updatesPanel').querySelectorAll('[data-update]').forEach(b => b.onclick = () => updateAction('updates_apply', b.dataset.update));
  H('updatesPanel').querySelectorAll('[data-tool]').forEach(b => b.onclick = () => updateAction('updates_launch', b.dataset.tool));
  H('updatesPanel').querySelectorAll('[data-rollback]').forEach(b => b.onclick = () => updateAction('updates_rollback', b.dataset.rollback));
  H('updateCheck').disabled = state.checking || state.busy;
  H('updateCheckLabel').textContent = state.checking ? 'Checking…' : 'Check for updates';
  H('updateChecked').textContent = state.checked ? 'Checked ' + new Date(state.checked * 1000).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}) : '';
  H('updateRestart').hidden = !state.ready; H('updateRestart').disabled = state.busy;
  const operation = state.busy || state.message && !state.checking && !state.message.startsWith('Checks finished.') && !state.message.startsWith('App update ready.');
  H('updateOperation').hidden = !operation;
  H('updateStatus').textContent = state.message || '';
  H('updateProgress').textContent = state.busy ? state.progress == null ? 'Working in the background…' : Math.round(state.progress * 100) + '% downloaded' : '';
  H('updateCancel').hidden = !state.busy;
  paintNvpiOpening();

}

function paintExtraTools(state) {
  if (!H('extraTools')) return;
  const key = JSON.stringify([state.items, state.busy, state.checking]);
  if (H('extraTools').dataset.content === key) return;
  H('extraTools').dataset.content = key;
  H('extraTools').innerHTML = EXTRA_TOOLS.map(tool => {
    const row = state.items?.find(x => x.id === tool.id);
    const open = tool.id === 'openmouse' || row?.launch;
    return `<div class="card extra-tool"><div class="extra-tool-icon">${svg(tool.icon)}</div><h3>${tool.name}</h3><p>${tool.text}</p>
      ${tool.id !== 'openmouse' ? versionLabels(row || {}) : ''}
      <div class="row"><button class="btn ghost" data-extra-tool="${tool.id}" ${!open ? 'disabled' : ''}>${tool.id === 'openmouse' ? 'Open in browser' : 'Open'}</button>
      ${row?.action ? `<button class="btn" data-extra-update="${tool.id}" ${state.busy || state.checking ? 'disabled' : ''}>${textEscape(row.action)}</button>` : ''}</div></div>`;
  }).join('');
  H('extraTools').querySelectorAll('[data-extra-tool]').forEach(b => b.onclick = () => updateAction('updates_launch', b.dataset.extraTool));
  H('extraTools').querySelectorAll('[data-extra-update]').forEach(b => b.onclick = () => updateAction('updates_apply', b.dataset.extraUpdate));
  paintNvpiOpening();
}

async function pageUpdates() {
  pageShell('Extra Tools', {crumb:'Tools › Extra Tools', text:'Open a tool to get started.'}, '<div id="extraTools" class="extra-tools"></div>');
  paintExtraTools(updateLast || {items:[], checking:true});
  const state = await api('updates_status');
  if (state?.items) { updateLast = state; paintUpdates(state); }
}

let activeTool = null;
function toolVisibility(key, visible) {
  if (key === 'nvpi') setNvpiOpening(false);
  let backdrop = H('toolBackdrop');
  if (!backdrop) {
    backdrop = document.createElement('div'); backdrop.id = 'toolBackdrop';
    backdrop.setAttribute('aria-label', 'Hide tool and keep it running');
    backdrop.title = 'Click outside the tool to hide it. Open restores this session.';
    backdrop.innerHTML = `<div id="toolFrame"><div id="toolGrip" title="Drag to move TechLoungeTweaks"><i></i></div><button id="toolClose" aria-label="Close tool" title="Close tool"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 7l10 10M17 7L7 17"/></svg></button></div>`;
    backdrop.onclick = e => { if (e.target === backdrop && activeTool) api('tools_hide', activeTool); };
    backdrop.querySelector('#toolGrip').onmousedown = e => { if (e.button === 0) { e.preventDefault(); api('start_drag'); } };
    backdrop.querySelector('#toolClose').onclick = async e => {
      e.stopPropagation();
      if (activeTool) {
        const result = await api('tools_close', activeTool);
        if (result?.ok === false && result.message) banner(result.message);
      }
    };
    document.body.appendChild(backdrop);
  }
  if (visible) { activeTool = key; closeUpdates(); backdrop.hidden = false; }
  else if (activeTool === key) { activeTool = null; backdrop.hidden = true; }
}

// Native tool windows must yield both painting and input to these shell panels.
let shellOverlayFrame = null;
let shellOverlaySignature = '';
function syncShellOverlays() {
  if (shellOverlayFrame !== null) return;
  shellOverlayFrame = requestAnimationFrame(async () => {
    shellOverlayFrame = null;
    const regions = ['updatesPanel','themepop'].map(id => H(id)).filter(el =>
      el && !el.hidden && getComputedStyle(el).display !== 'none').map(el => {
        const r = el.getBoundingClientRect(), margin = 18;
        return [r.x-margin,r.y-margin,r.width+margin*2,r.height+margin*2,window.devicePixelRatio || 1];
      });
    const signature = JSON.stringify(regions);
    if (signature === shellOverlaySignature) return;
    shellOverlaySignature = signature;
    const result = await api('tools_overlay_regions', regions);
    if (result?.ok === false) shellOverlaySignature = '';
  });
}
function watchShellOverlay(el) {
  new ResizeObserver(syncShellOverlays).observe(el);
  new MutationObserver(syncShellOverlays).observe(el,{attributes:true,attributeFilter:['hidden','class','style']});
  syncShellOverlays();
}
window.addEventListener('resize', syncShellOverlays);
