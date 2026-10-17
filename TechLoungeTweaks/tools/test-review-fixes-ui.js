const {chromium}=require(process.env.PW||'playwright');
const {pathToFileURL}=require('url');
const path=require('path');
const assert=require('assert');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME});
 try {
 const page=await browser.newPage({viewport:{width:940,height:640}});
 await page.goto(pathToFileURL(path.resolve(__dirname,'../src/web/index.html')).href);
 await page.evaluate(()=>{
  document.body.classList.remove('booting');H('bootlayer')?.remove();
  STATE.cats=['Performance','Networking'];
  STATE.tweaks=[{key:'good',name:'Good',desc:'A setting',category:'Performance',applied:false},{key:'bad',name:'Bad',desc:'A setting',category:'Performance',applied:false},{key:'unknown',name:'Unknown',desc:'A setting',category:'Performance',applied:false},{key:'network',name:'Network',category:'Networking',applied:false}];
  window.calls=[];window.confirmAction=async()=>true;
  window.api=async(n,...args)=>{
   calls.push([n,...args]);
   if(n==='bulk'||n==='bulk_tweaks')return{ok:false,applied:{good:true,bad:false,unknown:null,network:false},errors:{bad:'Write refused',unknown:'Cannot verify'}};
   if(n==='nvprofile_status')return{nvidia:false};
   if(n==='active_jobs')return[];
   return null;
  };
  buildNav();wireBulk();show('Performance');
 });
 await page.evaluate(()=>applyAll(true));
 assert.strictEqual(await page.locator('[data-key="good"] .badge').innerText(),'APPLIED');
 assert.strictEqual(await page.locator('[data-key="bad"] .badge').innerText(),'NOT APPLIED');
 assert.strictEqual(await page.locator('[data-key="unknown"] .badge').innerText(),'UNKNOWN');
 await page.evaluate(()=>{show('Networking');return netBulk(true);});
 assert.strictEqual(await page.evaluate(()=>STATE.tweaks.find(t=>t.key==='network').applied),false);
 await page.evaluate(()=>{show('Home');return runBulk('revert');});
 assert.match(await page.locator('#bulkStatus').innerText(),/failures or unverified/);
 assert(!(await page.evaluate(()=>calls.some(c=>c[0]==='nvprofile_set'))));
 const names=await page.locator('[data-nav]').evaluateAll(es=>es.map(e=>e.dataset.nav));
 assert.strictEqual(names.length,23);
 for(const group of ['GENERAL','TWEAKS','SYSTEM','TOOLS']) {
  await page.evaluate(group=>setNavGroup(group,true),group);
  assert.strictEqual(await page.locator('[data-navgroup="'+group+'"] .navsec').getAttribute('aria-expanded'),'true');
  const overflow=await page.locator('#navlist').evaluate(e=>e.scrollHeight-e.clientHeight);
  assert(overflow<=1,group+' sidebar overflow '+overflow);
 }
 await page.evaluate(()=>{revealNav('Home');});
 await page.locator('[data-nav="Home"]').focus();await page.keyboard.press('Enter');
 assert.strictEqual(await page.locator('#ptitle').innerText(),'Overview');
 await page.evaluate(()=>{window.calls=[];show('Disk Cleanup');CLEAN=[{id:'user_temp',name:'Temp',bytes:1,human:'1 B',default:true,desc:'Temp'}];renderClean();window.api=async(n,...a)=>{calls.push([n,...a]);return{ok:false,message:'Rejected'};};});
 await page.evaluate(()=>runClean());
 assert.deepStrictEqual(await page.evaluate(()=>calls.find(c=>c[0]==='clean_run')),['clean_run',['user_temp']]);
 console.log('PASS: authoritative bulk states, unknown state, restore scope, category IDs, all navigation groups and keyboard access at minimum size.');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
