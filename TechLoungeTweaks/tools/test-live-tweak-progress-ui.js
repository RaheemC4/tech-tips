const {chromium}=require(process.env.PW||'playwright');
const {pathToFileURL}=require('url');
const path=require('path');
const fs=require('fs');
const assert=require('assert/strict');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME});
 try {
  const page=await browser.newPage({viewport:{width:1160,height:780}});
  await page.goto(pathToFileURL(path.resolve(__dirname,'../src/web/index.html')).href);
  await page.evaluate(()=>{
   document.body.classList.remove('booting');H('bootlayer')?.remove();
   STATE.cats=['Privacy'];STATE.tweaks=[
    {key:'telemetry',name:'Disable Telemetry',desc:'Use the lowest diagnostic level supported by Windows.',category:'Privacy',applied:false},
    {key:'ceip',name:'Disable Experience Program',desc:'Opt out of the customer experience programme.',category:'Privacy',applied:false}
   ];
   window.confirmAction=async()=>true;
   window.api=async(name,...args)=>{
    if(name==='bulk'){
     window.progressOperation=args[2];
     return await new Promise(resolve=>window.resolveProgressFixture=resolve);
    }
    if(name==='active_jobs')return [];
    return null;
   };
   buildNav();wireBulk();show('Privacy');
   window.progressFixture=applyCategory('Privacy',true);
  });
  await page.waitForFunction(()=>window.progressOperation>0);
  assert.equal(await page.locator('[data-key="ceip"] .badge').innerText(),'QUEUED');
  await page.evaluate(()=>{
   window.onPy('tweak_progress',{operation:progressOperation,key:'telemetry',phase:'verified',completed:1,total:2,applied:true});
   window.onPy('tweak_progress',{operation:progressOperation,key:'ceip',phase:'working',completed:1,total:2});
  });
  assert.equal(await page.locator('[data-key="telemetry"] .sw').getAttribute('aria-checked'),'true');
  await page.waitForFunction(()=>{
   const control=document.querySelector('[data-key="telemetry"] .sw');
   return new DOMMatrix(getComputedStyle(control,'::after').transform).m41>18.9;
  });
  assert.equal(await page.locator('[data-key="ceip"] .badge').innerText(),'APPLYING…');
  assert.match(await page.locator('#psub').innerText(),/1 of 2 checked/);
  const folder=path.resolve(__dirname,'../docs');fs.mkdirSync(folder,{recursive:true});
  await page.screenshot({path:path.join(folder,'tweak-progress.png')});
  await page.evaluate(()=>{
   resolveProgressFixture({ok:true,applied:{telemetry:true,ceip:true},failed:[],errors:{}});
   return progressFixture;
  });
  assert.equal(await page.locator('[data-key="ceip"] .sw').getAttribute('aria-checked'),'true');
  assert.equal(await page.locator('[data-key="ceip"] .sw').isDisabled(),false);
  console.log('PASS: actual browser UI receives bridge progress before the pending batch returns, shows verified/working states and unlocks after final readback. Capture uses inert test data.');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
