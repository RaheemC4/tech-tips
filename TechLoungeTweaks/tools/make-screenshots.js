/*  Regenerate every screenshot in docs/.
 *
 *  Run this after ANY change that alters the UI - especially adding a page to
 *  the sidebar, because that changes every screenshot, not just the new one.
 *
 *      node tools/make-screenshots.js
 *
 *  Needs playwright + the bundled chromium. It drives web/index.html directly
 *  with a stubbed bridge, so no Windows build is required.
 */
const { chromium } = require(process.env.PW ||
  '/home/claude/.npm-global/lib/node_modules/playwright');
const CHROME = process.env.CHROME || '/opt/pw-browsers/chromium';
const D = __dirname + '/../docs/';
const PAGE = 'file://' + __dirname + '/../web/index.html';

const CAT={groups:['Runtimes','Browsers','Game clients'],winget:true,apps:[
 {id:'vcredist',name:'Visual C++ Redistributables (all)',group:'Runtimes',desc:"Every VC++ runtime from 2005 to 2022, x86 and x64. Fixes most 'missing MSVCP140.dll' style errors.",page:'#',route:'direct',installable:true},
 {id:'directx',name:'DirectX Runtime (web installer)',group:'Runtimes',desc:'The legacy DirectX 9/10/11 runtime components many older games still need.',page:'#',route:'direct',installable:true},
 {id:'dotnet8',name:'.NET Desktop Runtime 8',group:'Runtimes',desc:'Runtime for modern .NET desktop apps.',page:'#',route:'winget',installable:true},
 {id:'webview2',name:'Microsoft Edge WebView2',group:'Browsers',desc:'The runtime this app itself needs, and plenty of others.',page:'#',route:'winget',installable:true},
 {id:'edge',name:'Microsoft Edge',group:'Browsers',desc:'Edge stable. Brings WebView2 with it.',page:'#',route:'winget',installable:true},
 {id:'brave',name:'Brave',group:'Browsers',desc:'Chromium based, ad and tracker blocking built in.',page:'#',route:'winget',installable:true},
 {id:'chrome',name:'Google Chrome',group:'Browsers',desc:'Chrome stable, 64-bit.',page:'#',route:'winget',installable:true},
 {id:'firefox',name:'Mozilla Firefox',group:'Browsers',desc:'Firefox stable, 64-bit.',page:'#',route:'winget',installable:true},
 {id:'operagx',name:'Opera GX',group:'Browsers',desc:'The gaming-flavoured Opera build, with CPU and RAM limiters.',page:'#',route:'winget',installable:true},
 {id:'vivaldi',name:'Vivaldi',group:'Browsers',desc:'Chromium based, heavily customisable.',page:'#',route:'winget',installable:true},
 {id:'steam',name:'Steam',group:'Game clients',desc:"Valve's client.",page:'#',route:'winget',installable:true},
 {id:'epic',name:'Epic Games Launcher',group:'Game clients',desc:"Epic's client, and the free weekly games.",page:'#',route:'winget',installable:true},
 {id:'ubisoft',name:'Ubisoft Connect',group:'Game clients',desc:"Ubisoft's client.",page:'#',route:'winget',installable:true},
 {id:'eaapp',name:'EA App',group:'Game clients',desc:'Replaces Origin.',page:'#',route:'winget',installable:true},
 {id:'gog',name:'GOG Galaxy 2.0',group:'Game clients',desc:"GOG's client, DRM free.",page:'#',route:'winget',installable:true},
 {id:'battlenet',name:'Battle.net',group:'Game clients',desc:"Blizzard's client.",page:'#',route:'winget',installable:true},
 {id:'rockstar',name:'Rockstar Games Launcher',group:'Game clients',desc:"Rockstar's client.",page:'#',route:'direct',installable:true},
 {id:'amazon',name:'Amazon Games',group:'Game clients',desc:"Amazon's client, and the Prime Gaming freebies.",page:'#',route:'direct',installable:true}]};
const SPECS={CPU:'Intel Core i9-14900K',Graphics:'NVIDIA GeForce RTX 5090',Memory:'32 GB @ 6000 MT/s',Motherboard:'MSI MPG Z690 EDGE WIFI',Windows:'Windows 11 Pro (build 26200)',Storage:'Samsung SSD 990 PRO 2TB'};
const NV=[['Power Management Mode','Prefer maximum performance','Prefer maximum performance'],['Low Latency Mode','On','On'],['Vertical Sync','On','Off'],['Preferred Refresh Rate','Highest available','Highest available'],['G-SYNC','On (allowed)','Fixed refresh rate'],['G-SYNC Mode','Fullscreen & windowed','Off'],['Texture Filtering - Quality','High Performance','High Performance'],['Texture Filtering - Aniso Sample Optimization','On','On'],['Max Pre-Rendered Frames','1','1']];
const TW={Performance:[['Disable GameDVR','Turns off Xbox Game Bar background recording. One of the biggest free FPS wins on Windows 11.',1,null],['Enable Game Mode','Tells Windows to prioritise the running game and hold back background work.',1,null],['Disable Fullscreen Optimizations','Forces true exclusive fullscreen instead of the borderless compositor path.',1,null],['Disable Power Throttling','Stops Windows quietly downclocking background threads.',1,null],['Ultimate Performance Power Plan','Unlocks and activates the hidden Ultimate Performance plan.',1,null],['Foreground Priority Boost','Sets Win32PrioritySeparation so the focused app gets a longer CPU time slice.',0,null],['Gaming Task Priority','Raises the GPU and scheduling priority for the Games multimedia profile.',0,null],['Disable Memory Integrity','Turns off HVCI core isolation for 5-15% more CPU performance.',0,'Breaks Valorant, Vanguard and some anti-cheats']]};

(async () => {
  const b = await chromium.launch({ executablePath: CHROME });
  const p = await b.newPage({ viewport: { width: 1440, height: 1050 },
                              deviceScaleFactor: 2 });
  const boot = async () => {
    await p.goto(PAGE);
    await p.waitForTimeout(2600);
  };
  await boot();
   await p.evaluate(({NV,CAT})=>{document.body.classList.remove('booting','booting-slow');
  const bl=document.getElementById('bootlayer');if(bl)bl.remove();window.__gpu='nvidia';window.__CAT=CAT;
  window.api=async(n)=>{
   if(n==='nvprofile_status')return window.__gpu==='amd'
     ?{tool:true,profile:true,nvidia:false,gpu_name:'AMD Radeon RX 7900 XTX',state:'unknown',checked:true}
     :{tool:true,profile:true,defaults:true,backup:true,applied:false,state:'off',matched:0,total:39,checked:true,nvidia:true,releases_url:'#',tool_names:['x'],profile_name:'p'};
   if(n==='nvprofile_settings')return NV.map(r=>({name:r[0],current:r[1],target:r[2]}));
   if(n==='nvprofile_ready')return true;
   if(n==='defender_status')return{present:true,active:true,tamper:true,items:[['Real-time protection',1],['Behaviour monitoring',1],['On-access scanning',1],['Downloaded-file & web scanning',1],['Network inspection',1],['Tamper Protection',1]].map(i=>({label:i[0],on:!!i[1]}))};
   if(n==='app_catalog')return window.__CAT;
   if(n==='store_status')return{store:true,xbox:false,present:['Microsoft.WindowsStore']};
   if(n==='active_jobs')return[];
   return null;};},{NV,CAT});
 await p.evaluate(({SPECS,TW})=>{const cats=['Performance','Graphics','GPU','Networking','Power','Advanced','System','Privacy','Explorer & UI'];
  const cnt={Performance:[5,8],Graphics:[3,4],GPU:[2,4],Networking:[3,4],Power:[2,4],Advanced:[1,3],System:[3,5],Privacy:[9,11],'Explorer & UI':[6,7]};
  const out=[];for(const c of cats){const[on,tot]=cnt[c];const rows=TW[c];
   for(let i=0;i<tot;i++){const r=rows&&rows[i];
    out.push({key:c+i,name:r?r[0]:c+' tweak '+(i+1),desc:r?r[1]:'Adjusts a Windows setting in the '+c+' group.',category:c,applied:r?!!r[2]:i<on,icon:{Performance:'bolt',Graphics:'gpu',GPU:'gpu',Networking:'net',Power:'bolt',Advanced:'cpu',System:'wrench',Privacy:'shield','Explorer & UI':'folder'}[c],warning:r?r[3]:null});}}
  STATE.cats=cats;STATE.tweaks=out;STATE.snapshot=Object.fromEntries(out.map(t=>[t.key,t.applied]));
  renderSpecs(SPECS);buildNav();show('Home');refreshCounts();buildQuick();wireBulk();},{SPECS,TW});
 await p.waitForTimeout(1100);await p.screenshot({path:D+'home.png'});
 await p.evaluate(()=>show('Performance'));await p.waitForTimeout(700);await p.screenshot({path:D+'tweaks.png'});
 await p.evaluate(()=>show('NVIDIA Profile'));await p.waitForTimeout(1200);await p.screenshot({path:D+'nvidia.png'});
 await p.evaluate(()=>{window.__gpu='amd';show('NVIDIA Profile');});await p.waitForTimeout(1000);await p.screenshot({path:D+'nvidia-amd.png'});
 await p.evaluate(()=>{window.__gpu='nvidia';show('Defender');});await p.waitForTimeout(900);await p.screenshot({path:D+'defender.png'});
 // Resources mid-scan, with a real percentage
 await p.evaluate(()=>show('Resources'));await p.waitForTimeout(700);
 await p.evaluate(()=>{window.py_job({key:'res:sfc',kind:'resource',label:'System File Checker',state:'running',progress:0.42,line:'Verification 42% complete.',result:null});});
 await p.waitForTimeout(600);await p.screenshot({path:D+'resources.png'});
 await p.evaluate(()=>show('Install Apps'));await p.waitForTimeout(1400);
 await p.screenshot({path:D+'apps.png'});
 await p.evaluate(()=>window.py_job({key:'app:chrome',kind:'app',label:'Google Chrome',state:'running',progress:0.63,line:'Downloading from the vendor…',elapsed:12,result:null}));
 await p.waitForTimeout(600);await p.screenshot({path:D+'apps-installing.png'});
 
  // ---- pages that need their own stubbed bridge ----
  await boot();
   await p.evaluate(()=>{document.body.classList.remove('booting');const bl=document.getElementById('bootlayer');if(bl)bl.remove();
  window.api=async(n)=>{if(n==='virt_status')return{vt_firmware:true,hypervisor_present:true,
    launchtype:'auto',hvci:true,vbs_status:2,vbs_running:true,secureboot:true,tpm:true,
    virtualbox:true,virtualbox_version:'7.1.4',mode:'gaming',blockers:[],reboot_required:false};
   if(n==='active_jobs')return[];return null;};
  const cats=['Performance','Graphics'];const out=[];for(const c of cats)for(let i=0;i<4;i++)out.push({key:c+i,name:c+i,desc:'x',category:c,applied:i<2,icon:'cpu'});
  STATE.cats=cats;STATE.tweaks=out;buildNav();show('Home');refreshCounts();});
 await p.waitForTimeout(400);
 await p.evaluate(()=>show('Virtual Machines'));await p.waitForTimeout(1200);
 await p.screenshot({path:D+'virt.png'});
 
  await boot();
   await p.evaluate(()=>{document.body.classList.remove('booting','booting-slow');
  const bl=document.getElementById('bootlayer');if(bl)bl.remove();
  window.api=async()=>null;});
 await p.evaluate(({SPECS})=>{const cats=['Performance','Graphics','GPU','Networking','Power','Advanced','System','Privacy','Explorer & UI'];
  const cnt={Performance:[5,8],Graphics:[3,4],GPU:[2,4],Networking:[3,4],Power:[2,4],Advanced:[1,3],System:[3,5],Privacy:[9,11],'Explorer & UI':[6,7]};
  const out=[];for(const c of cats){const[on,tot]=cnt[c];for(let i=0;i<tot;i++)
    out.push({key:c+i,name:c+' tweak '+(i+1),desc:'Adjusts a Windows setting in the '+c+' group.',category:c,applied:i<on,icon:'cpu'});}
  STATE.cats=cats;STATE.tweaks=out;renderSpecs(SPECS);buildNav();show('Home');refreshCounts();buildQuick();wireBulk();wireTheme();},{SPECS});
 await p.waitForTimeout(700);

 // Networking with a completed test
 await p.evaluate(()=>{show('Networking');setTimeout(()=>{_nettest_done({grade:'A',verdict:'Great - stays responsive under load',
   download_mbps:1684,upload_mbps:141,idle_ms:7,loaded_ms:23,increase_ms:16,idle_jitter:1.1,jitter_ms:3.6,
   idle:{min:6,max:11,med:7,p25:6.5,p75:8,p95:10,jitter:1.1,n:24},
   down:{min:9,max:41,med:18,p25:13,p75:22,p95:30,jitter:3.6,n:44},
   up:{min:12,max:57,med:23,p25:17,p75:29,p95:44,jitter:3.2,n:44},
   activities:[['Web browsing',true],['Audio calls',true],['4K video streaming',true],['Video conferencing',true],['Low latency gaming',true]]});},400);});
 await p.waitForTimeout(1700);await p.screenshot({path:D+'network.png'});

 // System info
 await p.evaluate(()=>{pageShell('System Information',{crumb:'System › System Info',text:'What is actually inside this machine.'},
   `<div class="row" style="margin-bottom:12px"><button class="btn ghost">Re-read hardware</button>
     <span style="color:var(--faint);font-size:11.5px">Read once when the app opens.</span></div>
    <div class="row" style="margin-bottom:16px">${['CPU','Mainboard','Memory','Graphics','Storage','Network','Windows']
     .map((n,i)=>`<button class="btn ${i?'ghost':''}">${n}</button>`).join('')}</div>
    <div class="grid g3">${[
     [['Name','13th Gen Intel(R) Core(TM) i9-14900K'],['Cores','24'],['Logical processors','32'],['Max clock speed','5700 MHz'],['L3 cache','36 MB'],['Socket','LGA1700']],
     [['Model','MSI MPG Z690 EDGE WIFI'],['Manufacturer','Micro-Star International'],['BIOS','1.C0'],['BIOS date','2025-04-11'],['Chipset','Intel Z690'],['Secure Boot','On']],
     [['Total','32 GB'],['Speed','6000 MT/s'],['Slots used','2 of 4'],['Type','DDR5'],['Kit','G.Skill Trident Z5'],['XMP','Profile 1 active']],
    ].map(rows=>`<div class="card">${rows.map(([k,v])=>`<div style="padding:7px 0"><div class="label">${k}</div>
      <div style="font-weight:600;font-size:13px;margin-top:2px">${v}</div></div>`).join('')}</div>`).join('')}</div>`);});
 await p.waitForTimeout(700);await p.screenshot({path:D+'sysinfo.png'});

 // Theme picker open
 await p.evaluate(()=>{show('Home');wireTheme();document.getElementById('themebtn').click();});
 await p.waitForTimeout(700);await p.screenshot({path:D+'themes.png'});
 await p.evaluate(()=>{document.body.click();applyTheme('purple');show('Home');});
 await p.waitForTimeout(900);await p.screenshot({path:D+'theme-purple.png'});
 await p.evaluate(()=>applyTheme('blue'));
 
  await b.close();
  console.log('screenshots written to docs/');
})();
