const { chromium } = require(process.env.PW || 'playwright');
const { pathToFileURL } = require('url');
const path = require('path');
const assert = require('assert');
const catalog = require('../src/debloat_catalog.json');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME});
 try{
  const page=await browser.newPage({viewport:{width:1380,height:900}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(pathToFileURL(path.resolve(__dirname,'../src/web/index.html')).href);
  await page.evaluate(catalog=>{
   document.body.classList.remove('booting');H('bootlayer')?.remove();
   window.calls=[];
   window.api=async(name,...args)=>{
    window.calls.push([name,...args]);
    if(name==='debloat_status')return{ok:true,items:catalog.items.map(i=>({...i,applied:false,supported:i.id!=='StartAllAppsList'}))};
    if(name==='active_jobs')return[];
    if(name==='debloat_apply')return{ok:true,key:'debloat'};
    if(name==='job_state')return{key:'debloat',state:'done',result:{ok:true,message:'Finished test preset.'}};
    if(name==='bulk_tweaks')return{ok:true,applied:{bing_search:true,gamedvr:false,pause_windows_updates:true}};
    if(name==='nvprofile_status')return{nvidia:false};
    return null;
   };
   STATE.tweaks=[{key:'bing_search',category:'Explorer & UI',applied:false},{key:'gamedvr',category:'Performance',applied:false},{key:'pause_windows_updates',name:'Pause Windows Updates',desc:'Pause updates',category:'System',applied:false}];
   STATE.cats=['Explorer & UI','Performance','System'];buildNav();wireBulk();show('Debloat & Customization');
  },catalog);
  await page.locator('[data-debloat-choice="ShowKnownFileExt"]').waitFor();
  assert(await page.locator('[data-debloat-choice="ShowKnownFileExt"]').isChecked());
  assert(!(await page.locator('[data-debloat-choice="HideGallery"]').isChecked()));
  assert(await page.locator('[data-debloat-choice="StartAllAppsList"]').isDisabled());
  assert.strictEqual(await page.locator('[data-debloat-choice="DisableBing"]').count(),0);
  await page.locator('#debloatRecommended').click();
  await page.waitForFunction(()=>!BULK_BUSY);
  const tabCalls=await page.evaluate(()=>window.calls.filter(c=>['bulk_tweaks','debloat_apply','defender_set','nvprofile_set','virt_set'].includes(c[0])));
  assert.deepStrictEqual(tabCalls,[['bulk_tweaks','recommended',false],['debloat_apply','recommended',[],false]]);
  await page.evaluate(()=>{window.calls=[];show('Home');});
  await page.locator('#bulkRow [data-bulk="recommended"]').click();
  await page.waitForFunction(()=>!BULK_BUSY);
  assert.deepStrictEqual(await page.evaluate(()=>window.calls.filter(c=>['bulk_tweaks','debloat_apply','defender_set','nvprofile_set','virt_set'].includes(c[0]))),tabCalls);
  await page.evaluate(()=>{window.calls=[];show('Debloat & Customization');});
  await page.locator('[data-debloat-choice="ShowKnownFileExt"]').waitFor();
  await page.locator('[data-debloat-action="all"]').click();
  assert.strictEqual(await page.evaluate(()=>window.calls.filter(c=>c[0]==='debloat_apply').length),0);
  await page.getByRole('button',{name:'Cancel',exact:true}).click();
  assert.strictEqual(await page.evaluate(()=>window.calls.filter(c=>c[0]==='debloat_apply').length),0);
  await page.locator('[data-debloat-action="all"]').click();
  await page.locator('#confirmActionYes').click();
  await page.waitForFunction(()=>window.calls.some(c=>c[0]==='debloat_apply'));
  assert.strictEqual(await page.evaluate(()=>window.calls.find(c=>c[0]==='debloat_apply')[3]),true);
  await page.evaluate(()=>{show('Home');window.calls=[];});
  await page.locator('[data-bulk="all"]').click();
  await page.getByRole('button',{name:'Cancel',exact:true}).click();
  assert.strictEqual(await page.evaluate(()=>window.calls.filter(c=>c[0]==='bulk_tweaks').length),0);
  for(const mode of ['recommended','all']) {
   await page.evaluate(()=>{STATE.tweaks.find(t=>t.key==='pause_windows_updates').applied=false;show('Home');window.calls=[];});
   await page.locator('#bulkRow [data-bulk="'+mode+'"]').click();
   if(mode==='all')await page.locator('#confirmActionYes').click();
   await page.waitForFunction(()=>calls.some(c=>c[0]==='bulk_tweaks')&&!BULK_BUSY);
   assert(await page.evaluate(()=>STATE.tweaks.find(t=>t.key==='pause_windows_updates').applied));
   await page.evaluate(()=>show('System'));
   assert(await page.locator('[data-sw="pause_windows_updates"]').evaluate(el=>el.classList.contains('on')));
   assert.strictEqual(await page.locator('[data-key="pause_windows_updates"] .badge').innerText(),'APPLIED');
  }
  await page.setViewportSize({width:940,height:640});
  await page.evaluate(()=>show('Debloat & Customization'));
  await page.locator('[data-debloat-choice="ShowKnownFileExt"]').waitFor();
  assert(await page.locator('#debloatRecommended').isVisible());
  assert.deepStrictEqual(errors,[]);
  console.log('PASS: recommended parity, safe routes, exact preselection, build gating, Apply All confirmation, minimum size.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
