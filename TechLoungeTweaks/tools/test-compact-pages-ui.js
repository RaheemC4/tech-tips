const {chromium}=require(process.env.PW || 'playwright');
const {pathToFileURL}=require('url');
const path=require('path');
const assert=require('assert');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME});
 try {
  const page=await browser.newPage({viewport:{width:1320,height:832}});
  const errors=[];page.on('pageerror',e=>(errors.push(e.message),console.error(e.message)));
  await page.addInitScript(()=>{
   window.cleanCalls=0;
   window.pywebview={api:{init:async()=>{if(document.readyState!=='complete')await new Promise(resolve=>window.addEventListener('load',resolve,{once:true}));return {tweaks:[],categories:['Performance','Graphics','GPU','Networking','Power','Advanced','System','Privacy','Explorer & UI'],admin:true,specs:{CPU:'Intel Core i9-14900K',Graphics:'NVIDIA GeForce RTX 5090',Memory:'32 GB @ 4000 MT/s',Motherboard:'Micro-Star International Co., Ltd. MPG Z690 EDGE WIFI DDR4 (MS-7D31)',Windows:'Microsoft Windows 11 Pro (build 26300)',Storage:'CT2000MX500SSD1'},scanning:true};},
    clean_scan:async()=>({disk:{used:100,total:200,usedH:'100 GB',totalH:'200 GB',freeH:'100 GB'},items:Array.from({length:9},(_,i)=>({id:'test'+i,name:'Cleanup category '+i,desc:'Files used by Windows and apps. Locked files are skipped.',files:45,bytes:100,human:'100 B',default:true}))}),
    clean_run:()=>{cleanCalls++;return new Promise(resolve=>window.finishClean=resolve);},
    defender_status:async()=>({present:true,active:true,items:[]}),
    nvprofile_status:async()=>({nvidia:true,tool:true,profile:true,applied:true}),nvprofile_ready:async()=>true,
    nvprofile_settings:async()=>Array.from({length:39},(_,i)=>({name:'NVIDIA setting '+i,current:'Driver default',target:'Highest available'}))}};
  });
  await page.goto(pathToFileURL(path.resolve(__dirname,'../src/web/index.html')).href);
  await page.waitForFunction(()=>document.body.classList.contains('launch-ready'));
  await page.evaluate(()=>show('Disk Cleanup'));
  await page.waitForSelector('[data-cl]');
  assert(await page.locator('.clean-list').evaluate(e=>e.getBoundingClientRect().height<560));
  await page.locator('#cleanRun').click();
  assert(await page.locator('#cleanRun').isDisabled());
  assert.strictEqual(await page.locator('#cleanRun').getAttribute('aria-busy'),'true');
  assert((await page.locator('#cleanStatus').innerText()).includes('Cleaning selected'));
  await page.evaluate(()=>{runClean();});assert.strictEqual(await page.evaluate(()=>cleanCalls),1);
  await page.evaluate(()=>{document.getElementById('scroll').scrollTop=300;py_cleanlog({name:'Your temp files',freed:'100 B',skipped:2});});
  const position=await page.locator('#cleanStatus').boundingBox();assert(position.y>0&&position.y<250,'Progress stays at top while scrolling');
  await page.evaluate(()=>show('Home'));
  await page.evaluate(()=>show('Disk Cleanup'));
  assert(await page.locator('#cleanRun').isDisabled());
  assert((await page.locator('#cleanStatus').innerText()).includes('Your temp files'));
  await page.evaluate(()=>{show('Home');finishClean({ok:true,freed:'100 B',skipped:2});});
  await page.waitForTimeout(1300);assert.strictEqual(await page.locator('#ptitle').innerText(),'Overview');
  await page.evaluate(()=>show('Disk Cleanup'));await page.waitForSelector('[data-cl]');
  assert((await page.locator('#cleanStatus').innerText()).includes('Freed 100 B'));
  await page.locator('#cleanRun').click();await page.evaluate(()=>finishClean({ok:false,message:'Test error'}));
  await page.waitForFunction(()=>document.getElementById('cleanStatus')?.textContent==='Test error');
  assert(!(await page.locator('#cleanRun').isDisabled()));
  await page.evaluate(()=>show('NVIDIA Profile'));await page.waitForSelector('.nvrow');
  assert(await page.locator('.nvrow').first().evaluate(e=>e.getBoundingClientRect().height<=40));
  await page.evaluate(()=>show('Networking'));
  assert(await page.locator('#connRows').evaluate(e=>e.getBoundingClientRect().height<110));
  await page.evaluate(()=>show('Disk Cleanup'));await page.waitForSelector('[data-cl]');
  for(const width of [940,1320]){
   await page.setViewportSize({width,height:832});
   await page.evaluate(()=>{show('Networking');setNavGroup('SYSTEM',true);setNavGroup('TOOLS',true);});
   assert(await page.locator('[data-nav="Home"]').isVisible());
   assert.strictEqual(await page.locator('[data-navgroup-toggle="GENERAL"]').count(),0);
   assert(await page.locator('#scroll').evaluate(e=>e.scrollWidth===e.clientWidth));
   await page.evaluate(()=>show('NVIDIA Profile'));await page.waitForSelector('.nvrow');
   assert(await page.locator('#scroll').evaluate(e=>e.scrollWidth===e.clientWidth));
  }
  await page.evaluate(()=>show('Home'));
  await page.keyboard.press('Tab');
  await page.locator('[data-nav="Home"]').focus();
  assert.strictEqual(await page.locator('[data-nav="Home"]').evaluate(e=>getComputedStyle(e).outlineOffset),'-3px');
  await page.keyboard.press('Tab');
  assert.strictEqual(await page.evaluate(()=>document.activeElement.dataset.navgroupToggle),'TWEAKS');
  await page.keyboard.press('Enter');
  await page.keyboard.press('Tab');
  assert.strictEqual(await page.evaluate(()=>document.activeElement.dataset.nav),'Performance');
  await page.locator('#themebtn').focus();await page.keyboard.press('Enter');
  assert(await page.evaluate(()=>document.activeElement.matches('.tsw')));
  await page.keyboard.press('Tab');await page.keyboard.press('Enter');
  assert.strictEqual(await page.evaluate(()=>document.activeElement.id),'themebtn');
  assert.strictEqual(await page.locator('#themebtn').getAttribute('aria-expanded'),'false');
  await page.evaluate(()=>show('NVIDIA Profile'));await page.waitForSelector('#nvTgl:not(:disabled)');
  await page.locator('#nvTgl').focus();await page.keyboard.press('Space');
  assert.strictEqual(await page.evaluate(()=>document.activeElement.id),'nvNo');
  assert(await page.locator('#shell').evaluate(e=>e.inert));
  await page.keyboard.press('Tab');assert.strictEqual(await page.evaluate(()=>document.activeElement.id),'nvYes');
  await page.keyboard.press('Shift+Tab');assert.strictEqual(await page.evaluate(()=>document.activeElement.id),'nvNo');
  await page.keyboard.press('Escape');
  assert.strictEqual(await page.evaluate(()=>document.activeElement.id),'nvTgl');
  assert(!(await page.locator('#shell').evaluate(e=>e.inert)));
  await page.evaluate(()=>show('Defender'));await page.waitForSelector('#defTgl:not(:disabled)');
  await page.locator('#defTgl').focus();await page.keyboard.press('Enter');
  assert.strictEqual(await page.evaluate(()=>document.activeElement.id),'defNo');
  await page.keyboard.press('Escape');
  await page.evaluate(()=>show('Networking'));
  await page.locator('#page-generic .info').first().focus();assert(await page.locator('#tip').evaluate(e=>e.classList.contains('show')));
  await page.keyboard.press('Escape');assert(!(await page.locator('#tip').evaluate(e=>e.classList.contains('show'))));
  for(const [grade,ms,value,width] of [['A+',4,6,'100%'],['A',5,5,'83.3333%'],['B',30,4,'66.6667%'],['C',60,3,'50%'],['D',200,2,'33.3333%'],['F',400,1,'16.6667%']]) {
   await page.evaluate(({grade,ms})=>paintNetResult({grade,increase_ms:ms,verdict:'Test',idle_ms:7,loaded_ms:ms+7}),{grade,ms});
   assert.strictEqual(await page.locator('#gradeMeter').getAttribute('aria-valuenow'),String(value));
   assert.strictEqual(await page.locator('#gradeBar').evaluate(e=>e.style.width),width);
  }
  assert((await page.locator('.grade-legend').innerText()).includes('Added latency (ms)'));
  await page.setViewportSize({width:1320,height:832});
  await page.evaluate(()=>show('Home'));
  assert(await page.locator('.statgrid').evaluate(e=>e.getBoundingClientRect().height<215));
  for (const viewport of [{width:1280,height:800},{width:1320,height:832},{width:1370,height:856}]) {
    await page.setViewportSize(viewport);
    const fit = await page.locator('#scroll').evaluate(e=>({height:e.clientHeight,content:e.scrollHeight}));
    assert(fit.content<=fit.height+1,`Home must fit without scrolling at ${JSON.stringify(viewport)}: ${JSON.stringify(fit)}`);
    assert(await page.locator('#quickRow').evaluate(e=>e.getBoundingClientRect().bottom <= document.getElementById('scroll').getBoundingClientRect().bottom));
    assert.strictEqual(await page.locator('#quickRow button').count(),5);
  }
  await page.evaluate(()=>document.getElementById('scoreNum').textContent='96');
  const score = await page.locator('.ringwrap').evaluate(e=>{
    const ring=e.getBoundingClientRect(),value=e.querySelector('.val').getBoundingClientRect(),number=e.querySelector('b');
    return {width:ring.width,cx:ring.x+ring.width/2,valueCx:value.x+value.width/2,spacing:getComputedStyle(number).letterSpacing,size:parseFloat(getComputedStyle(number).fontSize)};
  });
  assert.strictEqual(score.width,122);assert.strictEqual(score.size,38);assert(['normal','0px'].includes(score.spacing));
  assert(Math.abs(score.cx-score.valueCx)<1);
  if(process.env.SCREENSHOT) {await page.waitForTimeout(1100);await page.evaluate(()=>{document.getElementById('scoreNum').textContent='96';document.getElementById('ring').style.strokeDashoffset='19.6';document.getElementById('scoreNote').textContent='Just about everything is applied.';});await page.screenshot({path:process.env.SCREENSHOT});}
  assert.deepStrictEqual(errors,[]);
  console.log('PASS: compact cleanup/NVIDIA/network layouts, immediate and sticky cleanup progress, duplicate guard, completion/error recovery, navigation safety, permanently visible Home, keyboard focus/activation/dialog return, compact Home, and all six grade meter levels.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
