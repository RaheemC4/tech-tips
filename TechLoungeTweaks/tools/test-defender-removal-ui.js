const {chromium}=require(process.env.PW||'playwright');
const {pathToFileURL}=require('url');
const path=require('path');
const assert=require('assert');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME});
 try {
  const page=await browser.newPage({viewport:{width:1200,height:800}});
  await page.goto(pathToFileURL(path.resolve(__dirname,'../src/web/index.html')).href);
  await page.evaluate(()=>{
   document.body.classList.remove('booting');H('bootlayer')?.remove();
   window.calls=[];window.removalFixture={running:false,phase:'idle'};
   window.api=async(name,...args)=>{
    calls.push([name,...args]);
    if(name==='defender_remover_machine')return {antivirus:false,security_app:false,security_registration_only:true,files:true,engine_running:false,recommended:'files',guidance:'Remove remaining folders next.'};
    if(name==='defender_remover_status')return removalFixture;
    if(name==='defender_remover_open'){window.removalFixture={running:true,phase:'running',progress:35,message:'Fixture progress'};return {ok:true};}
    return [];
   };
   openDefenderRemoval();
  });
  await page.locator('[data-remove-mode="files"] .removal-next').waitFor();
  assert((await page.locator('#removalMachine').innerText()).includes('Not installed'));
  assert.strictEqual(await page.locator('.removal-state-grid > div').nth(1).locator('strong').innerText(),'Not installed');
  assert((await page.locator('[data-remove-mode="all"]').innerText()).includes('Windows Security only'));
  await page.locator('[data-remove-mode="all"]').click();
  assert.strictEqual(await page.evaluate(()=>calls.some(c=>c[0]==='defender_remover_open')),false);
  await page.locator('#cancelRemovalRun').click();
  await page.locator('[data-remove-mode="antivirus"]').click();
  await page.locator('#confirmRemovalRun').click();
  await page.waitForFunction(()=>H('removalStatus')?.textContent.includes('Fixture progress'));
  assert.deepStrictEqual(await page.evaluate(()=>calls.filter(c=>c[0]==='defender_remover_open')),[['defender_remover_open','antivirus',true]]);
  assert(await page.locator('[data-remove-mode="all"]').isDisabled());
  await page.locator('#removalDismiss').click();
  await page.evaluate(()=>openDefenderRemoval());
  await page.waitForFunction(()=>H('removalStatus')?.textContent.includes('Fixture progress'));
  await page.evaluate(()=>{window.removalFixture={running:false,phase:'failed',progress:0,message:'Partial failure fixture'};});
  await page.waitForFunction(()=>H('removalStatus')?.textContent.includes('Partial failure fixture'));
  assert(await page.locator('[data-remove-mode="all"]').isEnabled());
  await page.evaluate(async()=>{removalFixture.message='Removal sequence finished with warnings. Some components may remain. Restart Windows manually and refresh the machine state. Windows Security still reports an installed package before restart.';removalFixture.log_path='C:/Users/Raheem/AppData/Local/Temp/TechLounge-removal-fixture/operation.log';await pollRemoval();});
  await page.locator('.removal-log summary').click();
  await page.locator('#openRemovalLogFolder').click();
  assert(await page.evaluate(()=>calls.some(c=>c[0]==='defender_remover_log_folder'&&c.length===1)));
  await page.locator('.removal-log summary').click();
  for(const viewport of [{width:1200,height:800},{width:1000,height:680}]) {
    await page.setViewportSize(viewport);
    assert(await page.locator('.removal-card').evaluate(el=>el.scrollHeight<=el.clientHeight+1),'Removal card requires scrolling at '+JSON.stringify(viewport));
  }
  console.log('PASS: removal choice, confirmation, cancellation, progress, navigation persistence and failure display; no system changes.');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
