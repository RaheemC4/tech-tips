const {chromium} = require(process.env.PW || 'playwright');
const {pathToFileURL} = require('url');
const path = require('path');
const assert = require('assert');
(async () => {
 const browser = await chromium.launch({executablePath:process.env.CHROME});
 try {
  const page = await browser.newPage({viewport:{width:940,height:640}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(pathToFileURL(path.resolve(__dirname,'../src/web/index.html')).href);
  await page.evaluate(()=>{
   document.body.classList.remove('booting');H('bootlayer')?.remove();window.calls=[];
   window.updateFixture={busy:false,checking:false,checked:Date.now()/1000,message:'Checks finished.',items:[
    {id:'dlss',name:'DLSS Swapper',installed:'1.2.6.1',available:'1.2.6.1',launch:true},
    {id:'bcu',name:'Bulk Crap Uninstaller',installed:'6.2',available:'6.3',launch:true,action:'Update'},
    {id:'nvpi',name:'NVIDIA Profile Inspector',installed:'7.2.1',available:'7.2.1',launch:true},
    {id:'app',name:'TechLoungeTweaks',installed:'2026.09.10',available:'2026.09.10',status:'current'},
    {id:'mas',name:'Microsoft Activation Scripts',installed:'3.12'},
    {id:'win11debloat',name:'Win11Debloat',installed:'2026.08.24'},
    {id:'openmouse',name:'OpenMouse'}
   ]};
   window.api=async(name,...args)=>{calls.push([name,...args]);return name==='updates_status'?structuredClone(updateFixture):{ok:true};};
   STATE.cats=[];buildNav();show('Extra Tools');
  });
  await page.locator('[data-extra-tool="nvpi"]').click();
  assert.strictEqual(await page.locator('[data-extra-tool="nvpi"]').innerText(),'Opening…');
  assert(await page.locator('[data-extra-tool="nvpi"]').isDisabled());
  await page.evaluate(()=>{toolVisibility('nvpi',true);toolVisibility('nvpi',false);});
  assert(await page.locator('[data-extra-tool="nvpi"]').isEnabled());
  await page.locator('[data-extra-tool="openmouse"]').click();
  assert.deepStrictEqual(await page.evaluate(()=>calls.find(c=>c[0]==='updates_launch')),['updates_launch','nvpi']);
  assert.strictEqual(await page.getByRole('button',{name:'Install',exact:true}).count(),0);
  assert.strictEqual(await page.getByText('Keep your toolbox current').count(),0);
  assert.strictEqual(await page.locator('#updatesButtonLabel').innerText(),'1 tool update');
  await page.locator('#updatesButton').click();
  await page.locator('#updatesPanel').waitFor({state:'visible'});
  assert((await page.locator('#updateSummary').innerText()).includes('is up to date'));
  assert.strictEqual(await page.getByText('Win11Debloat',{exact:true}).count(),0);
  assert.strictEqual(await page.getByText('Microsoft Activation Scripts',{exact:true}).count(),0);
  assert(await page.locator('#updatesPanel .version-old').count()>0);
  assert(await page.locator('#updatesPanel .version-latest').count()>0);
  await page.locator('#updatesPanel [data-update="bcu"]').click();
  await page.waitForFunction(()=>calls.some(c=>c[0]==='updates_apply'));
  assert.deepStrictEqual(await page.evaluate(()=>calls.find(c=>c[0]==='updates_apply')),['updates_apply','bcu']);
  await page.locator('#updateCheck').click();
  assert.deepStrictEqual(await page.evaluate(()=>calls.find(c=>c[0]==='updates_check')),['updates_check']);
  await page.evaluate(()=>{updateFixture.busy=true;updateFixture.progress=.4;updateFixture.message='Downloading';paintUpdates(updateFixture);});
  assert(await page.locator('#updateCheck').isDisabled());
  assert(await page.locator('#updatesPanel [data-update="bcu"]').isDisabled());
  assert(await page.locator('#updateCancel').isVisible());
  await page.locator('#updateCancel').click();
  await page.evaluate(()=>{closeUpdates();show('Home');show('Extra Tools');openUpdates();});
  await page.waitForFunction(()=>H('updateProgress').textContent.includes('40%'));
  await page.keyboard.press('Escape');assert(await page.locator('#updatesPanel').isHidden());
  await page.evaluate(()=>{updateFixture.busy=false;updateFixture.items.find(x=>x.id==='bcu').action=null;paintUpdates(updateFixture);});
  assert.strictEqual(await page.locator('#updatesButtonLabel').innerText(),'Updates');
  await page.evaluate(()=>{
   updateFixture.items.find(x=>x.id==='app').available='2026-09-10T18:26:44+00:00';
   updateFixture.items.find(x=>x.id==='app').status='unavailable';
   updateFixture.items.find(x=>x.id==='app').check_error=true;
   updateFixture.message='Checks finished.';paintUpdates(updateFixture);openUpdates();
  });
  assert.strictEqual(await page.locator('#updateDetails').count(),0);
  assert.strictEqual(await page.locator('#updateAppRow .version-latest').count(),0);
  assert(!(await page.locator('#updateAppRow').innerText()).includes('T18:'));
  const footer=await page.locator('#updateCheck').boundingBox(); assert(footer.y+footer.height<=640);
  await page.evaluate(()=>{closeUpdates();show('Home');show('Extra Tools');});
  await page.evaluate(()=>document.dispatchEvent(new MouseEvent('mouseup',{button:3,cancelable:true})));
  await page.waitForFunction(()=>STATE.page==='Home');
  await page.evaluate(()=>document.dispatchEvent(new MouseEvent('mouseup',{button:4,cancelable:true})));
  await page.waitForFunction(()=>STATE.page==='Extra Tools');
  await page.evaluate(()=>toolVisibility('dlss',true));
  await page.locator('#toolBackdrop').click({position:{x:2,y:2}});
  assert.deepStrictEqual(await page.evaluate(()=>calls.find(c=>c[0]==='tools_hide')),['tools_hide','dlss']);
  await page.locator('#toolClose').click();
  assert.deepStrictEqual(await page.evaluate(()=>calls.find(c=>c[0]==='tools_close')),['tools_close','dlss']);
  await page.locator('#toolGrip').dispatchEvent('mousedown',{button:0});
  assert(await page.evaluate(()=>calls.some(c=>c[0]==='start_drag')));
  assert(!(await page.evaluate(()=>calls.some(c=>['close','minimize'].includes(c[0])))));
  await page.evaluate(()=>toolVisibility('dlss',false));
  assert(await page.locator('#toolBackdrop').isHidden());
  await page.evaluate(()=>{wireTheme();openUpdates();});
  await page.waitForFunction(()=>calls.some(c=>c[0]==='tools_overlay_regions' && c[1].length));
  await page.evaluate(()=>closeUpdates());
  await page.waitForFunction(()=>calls.filter(c=>c[0]==='tools_overlay_regions').at(-1)[1].length===0);
  await page.locator('#themebtn').click();
  await page.waitForFunction(()=>calls.filter(c=>c[0]==='tools_overlay_regions').at(-1)[1].length===1);
  assert(await page.locator('#themepop').isVisible());
  assert(await page.evaluate(()=>Number(getComputedStyle(H('themepop')).zIndex)>Number(getComputedStyle(H('toolBackdrop')).zIndex)));
  await page.locator('#themepop .tsw').first().click();
  await page.waitForFunction(()=>calls.filter(c=>c[0]==='tools_overlay_regions').at(-1)[1].length===0);
  assert.deepStrictEqual(errors,[]);
  console.log('PASS: separate update panel, accurate app/tool labels, bundled Open actions including NVPI, hidden internal components, version colours, update actions, cancellation and navigation.');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
