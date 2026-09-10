'use strict';
let WINDOWS_STATUS = null;
let WINDOWS_BUSY = false;
async function closeAppWindow(button) {
  button.disabled = true;
  button.textContent = '…';
  const result = await api('close');
  if (!result || result.ok === false) {
    button.disabled = false; button.textContent = '×';
    banner(result?.message || 'Could not reach the window. Try Alt+F4.');
  }
  // Permit retry if the host failed to destroy the native window.
  setTimeout(() => { button.disabled = false; button.textContent = '×'; }, 2500);
}
function setupMessage(message = '', loading = false, ok = null) {
  const target = H('windowsSetupMessage'); if (!target) return;
  target.replaceChildren();
  target.style.color = ok === true ? 'var(--good)' : ok === false ? 'var(--bad)' : 'var(--muted)';
  if (loading) { const spin = document.createElement('span'); spin.className = 'spin'; target.append(spin, ' '); }
  target.append(document.createTextNode(message));
  target.setAttribute('aria-busy', String(loading));
}
function setupBusy(busy) {
  WINDOWS_BUSY = busy;
  document.querySelectorAll('[data-windows-setup], #refreshWindowsStatus').forEach(button => { button.disabled = busy; });
}
function paintWindowsStatus(status) {
  const edition = H('windowsCurrentEdition'), activation = H('windowsActivationStatus');
  if (!edition || !activation) return;
  if (!status?.ok) {
    edition.textContent = 'Current Windows version unavailable.';
    activation.textContent = status?.message || 'Could not read Windows status. Try Refresh status.';
    return;
  }
  WINDOWS_STATUS = status;
  edition.textContent = 'Currently installed: ' + status.name + (status.version ? ' · ' + status.version : '') + (status.build ? ' · Build ' + status.build : '');
  activation.textContent = status.activated === true ? 'Activation: Windows is activated.' : status.activated === false ? 'Activation: Windows is not activated.' : 'Activation: status unavailable.';
  activation.style.color = status.activated === true ? 'var(--good)' : 'var(--muted)';
}
function alreadyActivated(status) {
  setupMessage();
  showModal(`<div class="modal-card" role="dialog" aria-modal="true"><h2>Windows is already activated</h2>
    <p style="margin:12px 0">${textEscape(status?.name || 'This Windows installation')}</p>
    <p style="color:var(--muted)">No activation is needed.</p>
    <button class="btn" id="activatedOkay" style="margin-top:20px">OK</button></div>`);
  H('activatedOkay').onclick = closeModal; H('activatedOkay').focus();
}
async function activateWindows() {
  if (WINDOWS_BUSY) return;
  setupMessage();
  // The status already displayed is enough to give immediate feedback. The
  // backend still rechecks before a real activation launch when it is needed.
  if (WINDOWS_STATUS?.activated === true) { alreadyActivated(WINDOWS_STATUS); return; }
  setupBusy(true); setupMessage('Checking activation and opening MAS…', true);
  try {
    const result = await api('windows_setup', 'activate');
    if (result?.status) paintWindowsStatus(result.status);
    if (result?.already_activated) alreadyActivated(result.status);
    else setupMessage(result?.message || 'Could not open activation.', false, !!result?.ok);
  } finally { setupBusy(false); }
}
const EDITION_NAMES = {Core:'Home',CoreN:'Home N',CoreSingleLanguage:'Home Single Language',Professional:'Pro',ProfessionalN:'Pro N',
  ProfessionalWorkstation:'Pro for Workstations',ProfessionalWorkstationN:'Pro N for Workstations',ProfessionalEducation:'Pro Education',
  Enterprise:'Enterprise',EnterpriseN:'Enterprise N',Education:'Education',EducationN:'Education N',EnterpriseS:'Enterprise LTSC',EnterpriseSN:'Enterprise LTSC N'};
function editionLabel(edition) { return EDITION_NAMES[edition] || edition; }
async function chooseWindowsEdition() {
  if (WINDOWS_BUSY) return;
  setupBusy(true); setupMessage('Loading available Windows editions…', true);
  showModal(`<div class="modal-card" role="dialog" aria-modal="true"><h2>Change Windows Version</h2>
    <p style="margin-top:16px"><span class="spin"></span> Reading editions supported by this PC…</p></div>`);
  H('modal').onclick = null;
  let result;
  try { result = await api('windows_editions'); } finally { setupBusy(false); }
  setupMessage();
  if (!result?.ok) { closeModal(); setupMessage(result?.message || 'Could not load editions.', false, false); return; }
  const targets = Array.isArray(result.targets) ? result.targets : [];
  showModal(`<div class="modal-card" role="dialog" aria-modal="true"><h2>Change Windows Version</h2>
    <p id="editionCurrentName" style="margin:12px 0;font-weight:600">Currently running: ${textEscape(result.name || editionLabel(result.current))}</p>
    <p style="color:var(--muted);line-height:1.6">Choose an edition supported by this installation. This does not upgrade Windows 10 to 11. A restart and activation may be needed.</p>
    <div id="editionOptions" class="edition-options" tabindex="0" role="group" aria-label="Available Windows editions">
      ${targets.map(target => `<button class="btn ghost" data-edition-target="${textEscape(target)}">${textEscape(editionLabel(target))}</button>`).join('') || '<p>No supported edition changes were reported by Windows.</p>'}
    </div><button class="btn ghost" id="editionCancel">Cancel</button></div>`);
  H('editionCancel').onclick = closeModal;
  document.querySelectorAll('[data-edition-target]').forEach(button => {
    button.onclick = async () => {
      const target = button.dataset.editionTarget;
      if (!await confirmAction('Change to Windows 11 ' + editionLabel(target) + '?',
        `Current edition: ${result.name || result.current}. Target: ${editionLabel(target)}. Save your work first. The new edition may require activation. This app will not restart the PC automatically.`, 'Change edition')) return;
      setupBusy(true); setupMessage('Changing Windows edition. Please wait…', true);
      showModal(`<div class="modal-card" role="dialog" aria-modal="true"><h2>Changing Windows edition</h2>
        <p style="margin-top:16px"><span class="spin"></span> Windows is processing the change to ${textEscape(editionLabel(target))}…</p>
        <p style="margin-top:12px;color:var(--muted)">This can take several minutes. Keep the app open.</p></div>`);
      H('modal').onclick = null;
      try {
        const changed = await api('windows_change_edition', target, true);
        WINDOWS_STATUS = null;
        closeModal();
        setupMessage(changed?.message || 'Windows did not return a result. Refresh status before retrying.', false, !!changed?.ok);
        showModal(`<div class="modal-card" role="dialog" aria-modal="true"><h2>${changed?.ok ? 'Restart needed' : 'Edition change did not complete'}</h2>
          <p style="margin:14px 0;line-height:1.6">${textEscape(changed?.message || 'Refresh status before retrying.')}</p>
          <button class="btn" id="editionDone">OK</button></div>`);
        H('editionDone').onclick = closeModal;
      } finally { setupBusy(false); }
    };
  });
}
function wireWindowsSetup() {
  document.querySelector('[data-windows-setup="activate"]').onclick = activateWindows;
  document.querySelector('[data-windows-setup="edition"]').onclick = chooseWindowsEdition;
  H('refreshWindowsStatus').onclick = async () => {
    if (WINDOWS_BUSY) return;
    setupBusy(true); setupMessage('Refreshing Windows status…', true);
    try { WINDOWS_STATUS = null; paintWindowsStatus(await api('windows_status')); setupMessage(); }
    finally { setupBusy(false); }
  };
  if (WINDOWS_STATUS) paintWindowsStatus(WINDOWS_STATUS);
  else {
    setupMessage('Reading Windows status…', true);
    api('windows_status').then(result => { paintWindowsStatus(result); if (!WINDOWS_BUSY) setupMessage(); });
  }
  setupBusy(WINDOWS_BUSY);
}
