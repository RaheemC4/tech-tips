const {chromium}=require(process.env.PW || 'playwright');
const {pathToFileURL}=require('url');
const path=require('path');
const assert=require('assert');
const NV=[
 ['Power Management Mode','Prefer maximum performance','Prefer maximum performance'],
 ['Low Latency Mode','On','On'],['Vertical Sync','On','Off'],['V-Sync Tear Control','Standard','Standard'],
 ['Preferred Refresh Rate','Default','Highest available'],['G-SYNC','On (allowed)','Fixed refresh rate'],
 ['G-SYNC Mode','Fullscreen & windowed','Off'],['Texture Filtering - Quality','Default','High Performance'],
 ['Texture Filtering - Aniso Sample Optimization','Off','On'],['Max Pre-Rendered Frames','Default','1']
];
const NET=[
 ["Disable Nagle's Algorithm",'Stops Windows bundling small packets together, which cuts a few ms off latency in online games.'],
 ['Network Throttling Off','Removes the 10-packet-per-ms multimedia throttle and lowers the multimedia CPU reservation to 10% (0 causes audio crackle).'],
 ['Disable Network Offloads','Turns off Chimney, RSC and packet coalescing so packets are not batched by the network card.'],
 ['Disable Firewall Popups',"Stops the 'Windows Defender Firewall has blocked some features' prompt every time a new game launches."]
];
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME});
 try {
  const page=await browser.newPage({viewport:{width:1280,height:800}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(({NV,NET})=>{
   const items=[{id:'app',name:'TechLoungeTweaks',installed:'2026.10.18.052434',available:'2026.10.18.052434',status:'current'},
    {id:'driverbooster',name:'IObit Driver Booster',installed:'13.5.1.400',local:true,launch:true},
    {id:'treesize',name:'TreeSize Professional',installed:'9.8.0.2301',local:true,launch:true},
    ...[['dlss','DLSS Swapper','v1.2.6.1'],['bcu','Bulk Crap Uninstaller','v6.3'],['nvpi','NVIDIA Profile Inspector','v7.2.1.6']].map(([id,name,version])=>({id,name,installed:version,available:version,launch:true}))];
   window.updateFixture={items,busy:false,checking:false,checked:Date.now()/1000,message:'Checks finished.'};
   window.pywebview={api:{init:async()=>{if(document.readyState!=='complete')await new Promise(resolve=>window.addEventListener('load',resolve,{once:true}));return {tweaks:NET.map(([name,desc],i)=>({key:'net'+i,name,desc,category:'Networking',applied:true,icon:'net'})),categories:['Networking'],admin:true,specs:{},scanning:false};},
    nvprofile_status:async()=>({nvidia:true,tool:true,profile:true,state:'partial',matched:19,total:39}),
    nvprofile_ready:async()=>true,nvprofile_settings:async()=>NV.map(([name,current,target])=>({name,current,target})),
    updates_status:async()=>structuredClone(updateFixture)}};
  },{NV,NET});
  await page.goto(pathToFileURL(path.resolve(__dirname,'../src/web/index.html')).href);
  await page.waitForFunction(()=>document.body.classList.contains('launch-ready'));
  async function fit(selector,label){
   const size=await page.locator(selector).evaluate(e=>({height:e.clientHeight,content:e.scrollHeight,width:e.clientWidth,contentWidth:e.scrollWidth}));
   assert(size.content<=size.height+1,`${label} vertical overflow: ${JSON.stringify(size)}`);
   assert(size.contentWidth<=size.width+1,`${label} horizontal overflow: ${JSON.stringify(size)}`);
  }
  for(const viewport of [{width:1280,height:800},{width:1320,height:832},{width:1370,height:856}]){
   await page.setViewportSize(viewport);
   await page.evaluate(()=>show('NVIDIA Profile'));await page.waitForSelector('.nvrow');
   assert.strictEqual(await page.locator('.nvrow').count(),10);
   await fit('#scroll','NVIDIA '+JSON.stringify(viewport));
   await page.evaluate(()=>show('Networking'));
   await page.evaluate(()=>paintNetResult({grade:'A+',verdict:'Excellent - no measurable lag under load',idle_ms:7,loaded_ms:11,increase_ms:4,download_mbps:1684,upload_mbps:131,idle:{med:7},down:{med:8},up:{med:11},idle_jitter:4,jitter_ms:63,activities:Array.from({length:5},(_,i)=>['Activity '+i,true])}));
   assert.strictEqual(await page.locator('#netTweakGrid .card').count(),4);
   await fit('#scroll','Networking '+JSON.stringify(viewport));
   await page.evaluate(()=>openUpdates());await page.waitForSelector('#updatesPanel:not([hidden])');
   assert.strictEqual(await page.locator('#updateToolRows .update-row').count(),5);
   await fit('#updatesPanel .update-body','Updates current '+JSON.stringify(viewport));
   await page.evaluate(()=>{updateFixture.busy=true;updateFixture.progress=.42;updateFixture.message='Downloading the app update. You can keep using the app while it finishes.';updateFixture.items.filter(x=>!x.local).forEach(x=>{x.action='Update';x.available=x.id==='app'?'2026.10.19.215654':'v9.9.9';if(x.id!=='app')x.rollback=true;});paintUpdates(updateFixture);});
   await fit('#updatesPanel .update-body','Updates downloading '+JSON.stringify(viewport));
   assert(await page.locator('#updateCancel').isVisible());
   assert.strictEqual(await page.locator('[data-rollback]').count(),0);
   assert(await page.locator('[data-tool="bcu"]').isVisible());
   const bounds=await page.locator('#updateCheck').boundingBox();assert(bounds.y+bounds.height<=viewport.height);
   await page.evaluate(()=>{updateFixture.busy=false;updateFixture.ready=true;updateFixture.message='App update ready.';paintUpdates(updateFixture);});
   await fit('#updatesPanel .update-body','Updates ready '+JSON.stringify(viewport));
   assert(await page.locator('#updateRestart').isVisible());
   await page.evaluate(()=>{closeUpdates();updateFixture.ready=false;updateFixture.items.forEach(x=>{delete x.action;delete x.rollback;if(x.available)x.available=x.installed;});updateFixture.message='Checks finished.';});
  }
  if(process.env.SCREENSHOT_DIR){
   for(const [route,file] of [['NVIDIA Profile','nvidia-fit.png'],['Networking','network-fit.png']]){
    await page.evaluate(route=>show(route),route);await page.waitForTimeout(600);
    await page.screenshot({path:path.join(process.env.SCREENSHOT_DIR,file)});
   }
   await page.evaluate(()=>openUpdates());await page.waitForTimeout(300);
   await page.screenshot({path:path.join(process.env.SCREENSHOT_DIR,'updates-fit.png')});
  }
  assert.deepStrictEqual(errors,[]);
  console.log('PASS: full ten-row NVIDIA profile, four network tweaks and completed results, all five update tools, downloading/cancellation and restart states fit without scrolling at three desktop viewports.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
