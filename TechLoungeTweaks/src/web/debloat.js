'use strict';
let DEBLOAT_SELECTION = null;
function textEscape(value) {
  const el = document.createElement('span'); el.textContent = String(value ?? ''); return el.innerHTML.replace(/"/g, '&quot;');
}
async function confirmAction(title, message, yes = 'Continue') {
  return new Promise(resolve => {
    showModal(`<div class="modal-card" role="dialog" aria-modal="true"><h2>${textEscape(title)}</h2>
      <p style="margin:14px 0;line-height:1.6;color:var(--muted)">${textEscape(message)}</p>
      <div class="row"><button class="btn" id="confirmActionYes">${textEscape(yes)}</button>
      <button class="btn ghost" id="confirmActionNo">Cancel</button></div></div>`);
    const finish = result => { closeModal(); resolve(result); };
    H('confirmActionYes').onclick = () => finish(true);
    H('confirmActionNo').onclick = () => finish(false);
    H('modal').onclick = e => { if (e.target === H('modal')) finish(false); };
    H('confirmActionNo').focus();
  });
}
function paintDebloatJob(job) {
  const status = H('debloatStatus'); if (!status || !job) return;
  status.hidden = false;
  const running = job.state === 'running';
  status.textContent = running ? `${job.line || 'Working…'} · ${job.elapsed || 0}s` : (job.result?.message || 'Finished.');
  const bar = H('debloatProgress');
  if (bar) { bar.style.display = running ? '' : 'none'; bar.querySelector('i').style.width = ((job.progress || 0) * 100) + '%'; }
  document.querySelectorAll('[data-debloat-action], [data-debloat-choice], [data-debloat-undo], #debloatRecommended').forEach(b => { b.disabled = running || b.dataset.unsupported === 'true'; });
}
async function waitForDebloat() {
  for (;;) {
    const job = await api('job_state', 'debloat');
    if (!job) return {ok:false,message:'Debloat progress is unavailable. Check the Debloat tab before retrying.'};
    paintDebloatJob(job);
    if (job.state !== 'running') {
      if (STATE.page === 'Debloat & Customization') await pageDebloat();
      return job.result;
    }
    await new Promise(resolve => setTimeout(resolve, 700));
  }
}
async function pageDebloat() {
  pageShell('Debloat & Customization', {crumb:'Tools › Debloat & Customization', text:'A curated Win11Debloat preset for your Windows 11 setup.'},
    `<div class="card"><b>Keep the essentials. Choose the rest.</b>
      <p style="color:var(--muted);line-height:1.6;margin:10px 0">Recommended keeps Xbox, Game Bar, Microsoft Store, printing, Windows Update, Defender and gaming settings intact.
      Bing search, ads and privacy settings already in other tabs are reused, not duplicated.</p>
      <p style="color:var(--muted);line-height:1.6;margin:10px 0">Switches select the next run; they do not apply immediately. Current state is shown separately.
      Removing apps affects all users. Pin clearing runs once per existing profile, so you can repin afterwards.</p>
      <div class="row" style="flex-wrap:wrap;gap:8px">
        <button class="btn" data-bulk="recommended" id="debloatRecommended">Apply Recommended</button>
        <button class="btn" data-debloat-action="selected">Apply Selected</button>
        <button class="btn ghost" data-debloat-action="all">Apply All</button>
        <button class="btn ghost" id="debloatRefresh">Refresh status</button>
      </div><p style="font-size:12px;color:var(--muted);margin-top:10px">Recommended is identical to the dashboard button, including the shared privacy options.</p>
      <div id="debloatStatus" class="bulkstatus" role="status" aria-live="polite">Reading Windows settings…</div>
      <div id="debloatProgress" class="jobbar" style="display:none"><i></i></div>
    </div><div id="debloatItems"></div>
    <p style="color:var(--muted);font-size:12px;margin-top:16px">Powered by Raphire/Win11Debloat · MIT licence. Unsupported Windows options are skipped.
      Registry values are checked; some UI policies depend on your Windows edition and rollout. Sign out or restart to see changes.</p>`);
  H('debloatRecommended').onclick = () => runBulk('recommended');
  H('debloatRefresh').onclick = pageDebloat;
  JOB_RENDERERS.debloat = paintDebloatJob;
  document.querySelectorAll('[data-debloat-action]').forEach(button => {
    button.onclick = async () => {
      const mode = button.dataset.debloatAction;
      if (mode === 'all' && !await confirmAction('Apply all debloat and customization options?', 'This also includes optional Gallery and duplicate-drive customization. Selected app packages will be removed for all users and existing Start pins cleared once. Xbox, Game Bar, Store and printing remain untouched.', 'Apply All')) return;
      button.disabled = true;
      H('debloatStatus').textContent = 'Starting…';
      try {
        const result = await api('debloat_apply', mode, [...(DEBLOAT_SELECTION || [])], mode === 'all');
        if (!result?.ok) { H('debloatStatus').textContent = result?.message || 'Could not start.'; return; }
        await waitForDebloat();
      } finally { button.disabled = false; }
    };
  });
  const result = await api('debloat_status');
  if (STATE.page !== 'Debloat & Customization') return;
  if (!result?.ok) { H('debloatStatus').textContent = result?.message || 'Could not read current state.'; return; }
  if (!DEBLOAT_SELECTION) DEBLOAT_SELECTION = new Set(result.items.filter(i => i.recommended && i.supported).map(i => i.id));
  let html = '';
  for (const group of ['Customization','Debloat','Optional apps']) {
    html += `<div class="section" style="margin-top:22px">${group}</div><div class="grid g2">`;
    for (const item of result.items.filter(i => i.group === group)) {
      const state = !item.supported ? 'Needs Windows build ' + item.min_build + '+' : item.applied === null ? 'Status unavailable' : item.applied ? (item.kind === 'app' ? 'Not installed' : item.kind === 'pins' ? 'Already cleared once' : 'Setting applied') : 'Not applied';
      html += `<div class="card"><div class="row" style="justify-content:space-between;gap:12px"><b>${textEscape(item.title)}</b>
        <input type="checkbox" role="switch" aria-label="${textEscape(item.title)}" data-debloat-choice="${textEscape(item.id)}" data-unsupported="${!item.supported}" ${DEBLOAT_SELECTION.has(item.id) ? 'checked' : ''} ${!item.supported ? 'disabled' : ''}></div>
        <p style="font-size:12px;color:var(--muted);line-height:1.6;margin:10px 0">${textEscape(item.description)}</p>
        <div style="font-size:12px;color:${item.applied ? 'var(--good)' : 'var(--muted)'}">${textEscape(state)}${item.recommended ? ' · Recommended' : ' · Optional'}</div>
        ${item.kind === 'registry' && item.supported ? `<button class="btn ghost" style="margin-top:10px" data-debloat-undo="${textEscape(item.id)}">Undo setting</button>` : ''}</div>`;
    }
    html += '</div>';
  }
  H('debloatItems').innerHTML = html;
  H('debloatStatus').textContent = 'Ready. Review the selected options below.';
  document.querySelectorAll('[data-debloat-choice]').forEach(input => {
    input.onchange = () => input.checked ? DEBLOAT_SELECTION.add(input.dataset.debloatChoice) : DEBLOAT_SELECTION.delete(input.dataset.debloatChoice);
  });
  document.querySelectorAll('[data-debloat-undo]').forEach(button => {
    button.onclick = async () => {
      if (!await confirmAction('Undo this setting?', 'Apply the upstream inverse setting. This uses its default value, not an exact restore of your previous choice.', 'Undo setting')) return;
      const result = await api('debloat_apply', 'undo', [button.dataset.debloatUndo]);
      if (result?.ok) await waitForDebloat();
      else H('debloatStatus').textContent = result?.message || 'Could not undo setting.';
    };
  });
  restoreJobs();
}
