'use strict';
const REMOVAL_OPTIONS = [
  ['all','Defender + Windows Security','Remove the antivirus and the Windows Security app.'],
  ['antivirus','Defender antivirus','Keep the Windows Security app. Windows updates may restore Defender.'],
  ['files','Remaining Defender files','Use after removing the antivirus and restarting Windows.']
];
let removalTimer;
let removalWasRunning=false;
let removalMachine=null;
async function refreshRemovalMachine() {
  const target=H('removalMachine');if(!target)return;
  target.innerHTML='<span class="spin"></span> Reading this PC…';
  document.querySelectorAll('.removal-next').forEach(e=>e.remove());
  const machine=await api('defender_remover_machine');
  if(H('removalMachine')!==target)return;
  removalMachine=machine;
  const label=(value,yes,no)=>value===true?yes:value===false?no:'Unknown';
  target.innerHTML=`<div class="removal-state-grid">${[
    ['Defender antivirus',label(machine?.antivirus,'Installed','Not installed')],
    ['Windows Security app',machine?.security_registration_only?'Not installed':label(machine?.security_app,'Installed','Not installed')],
    ['Defender folders',label(machine?.files,'Still present','Not found')],
    ['Loaded components',label(machine?.engine_running,'Running / restart may be needed','None detected')]
  ].map(([name,value])=>`<div><small>${name}</small><strong>${value}</strong></div>`).join('')}</div>
  <p>${textEscape(machine?.guidance||'State unavailable. Refresh before choosing a removal step.')}</p>
  <button class="btn ghost" id="refreshRemovalMachine">Refresh state</button>`;
  H('refreshRemovalMachine').onclick=refreshRemovalMachine;
  const combined=document.querySelector('[data-remove-mode="all"]');
  if(combined && machine?.antivirus===false) {
    combined.querySelector('strong').textContent='Windows Security only';
    combined.querySelector('span').textContent=machine.security_registration_only?'Remove the remaining package registration.':'Remove Windows Security. Defender antivirus is already absent.';
  }
  if(machine?.recommended) {
    const button=document.querySelector(`[data-remove-mode="${machine.recommended}"]`);
    if(button){const badge=document.createElement('em');badge.className='removal-next';badge.textContent='Next step for full removal';button.prepend(badge);}
  }
}
async function openDefenderRemoval() {
  clearTimeout(removalTimer);
  showModal(`<div class="modal-card removal-card" role="dialog" aria-modal="true" aria-labelledby="removalTitle">
    <span class="removal-eyebrow">SYSTEM / DEFENDER</span><h2 id="removalTitle">Defender removal</h2>
    
    <div class="removal-layout"><section id="removalMachine" aria-live="polite"></section>
    <div class="removal-options">${REMOVAL_OPTIONS.map(([id,name,desc])=>`<button class="removal-option" data-remove-mode="${id}"><strong>${name}</strong><span>${desc}</span><b aria-hidden="true">›</b></button>`).join('')}</div></div>
    <p class="removal-note">Based on ionuttbara’s Defender Remover ${textEscape('release13-rev1')}. Antivirus removal also disables SmartScreen, UAC and mitigations. Security-only and remaining-files removal skip those changes. Recovery may require reinstalling Windows.</p>
    <section id="removalStatus" aria-live="polite" hidden></section>
    <div class="row" style="margin-top:18px"><button class="btn ghost" id="removalDismiss">Back to Defender</button></div>
  </div>`);
  H('removalDismiss').onclick=closeModal;
  document.querySelectorAll('[data-remove-mode]').forEach(button=>button.onclick=()=>confirmRemoval(button.dataset.removeMode));
  await Promise.all([pollRemoval(),refreshRemovalMachine()]);
}
async function pollRemoval() {
  if (!H('removalStatus')) return;
  const result=await api('defender_remover_status');
  if (!H('removalStatus')) return;
  document.querySelectorAll('[data-remove-mode]').forEach(b=>b.disabled=!!result?.running);
  if (result && result.phase!=='idle') {
    const target=H('removalStatus');target.hidden=false;
    const percent=Math.min(100,Math.max(0,Number(result.progress)||0));
    target.innerHTML=`<strong>${result.running?'Removal in progress':result.phase==='complete'?'Restart Windows when ready':'Removal needs attention'}</strong>
      <p>${textEscape(result.message||'')}</p><progress max="100" value="${percent}" aria-label="Removal progress"></progress>
      ${result.running?'<small>You can return to the app while this runs. Closing is disabled until it finishes.</small>':''}
      ${result.log_path?`<details class="removal-log"><summary>Log location</summary><small>${textEscape(result.log_path)}</small><button class="btn ghost" id="openRemovalLogFolder">Open log folder</button></details>`:''}`;
  }
  if(H('openRemovalLogFolder'))H('openRemovalLogFolder').onclick=async()=>{
    const response=await api('defender_remover_log_folder');
    if(!response?.ok)banner(response?.message||'Could not open the log folder.');
  };
  if (result?.running) removalTimer=setTimeout(pollRemoval,700);
  else if(removalWasRunning)refreshRemovalMachine();
  removalWasRunning=!!result?.running;
}
function confirmRemoval(mode) {
  const baseOption=REMOVAL_OPTIONS.find(o=>o[0]===mode);if(!baseOption)return;
  const securityOnly=mode==='all' && removalMachine?.antivirus===false;
  const option=securityOnly?['all','Windows Security only','Remove the Windows Security package. Skip antivirus removal and unrelated security settings.']:baseOption;
  clearTimeout(removalTimer);
  showModal(`<div class="modal-card removal-card" role="dialog" aria-modal="true" aria-labelledby="removalConfirmTitle">
    <span class="removal-eyebrow">CONFIRM REMOVAL</span><h2 id="removalConfirmTitle">${textEscape(option[1])}</h2>
    <p class="removal-intro">${textEscape(option[2])}</p>
    <p class="removal-note">${mode==='files'?'The remaining Defender program and data folders will be deleted.':securityOnly?'Only the Windows Security package will be removed.': 'This also disables SmartScreen, UAC, VBS and other security protections. You will have no Defender antivirus protection.'} This is not undone by the Defender toggle. Save your work and make a system backup first. Recovery may require reinstalling Windows.</p>
    <p class="removal-intro">Progress stays in this app. Windows will not restart automatically.</p>
    <div class="row"><button class="btn" id="confirmRemovalRun">Remove selected components</button><button class="btn ghost" id="cancelRemovalRun">Cancel</button></div>
  </div>`);
  H('cancelRemovalRun').onclick=openDefenderRemoval;
  H('confirmRemovalRun').onclick=async()=>{
    H('confirmRemovalRun').disabled=true;
    const result=await api('defender_remover_open',securityOnly?'security':mode,true);
    await openDefenderRemoval();
    if(!result?.ok)banner(result?.message||'Could not start removal.');
  };
}
