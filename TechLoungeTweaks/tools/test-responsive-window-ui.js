const {chromium}=require(process.env.PW || 'playwright');
const assert=require('assert');const {pathToFileURL}=require('url');const path=require('path');
(async()=>{const browser=await chromium.launch({executablePath:process.env.CHROME});try{
const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.addInitScript(()=>{window.resizeCalls=[];window.pywebview={api:{init:async()=>{if(document.readyState!=='complete')await new Promise(r=>window.addEventListener('load',r,{once:true}));return ({tweaks:[{key:'game',name:'Game Mode',desc:'Test setting',category:'Performance',applied:true,icon:'bolt'}],categories:['Performance'],admin:true,specs:{CPU:'Example CPU'},scanning:false});},reveal:async()=>true,start_resize:async(edge)=>{resizeCalls.push(edge);return true;}}};});
await page.goto(pathToFileURL(path.resolve(__dirname,'../src/web/index.html')).href);
try{await page.waitForFunction(()=>document.body.classList.contains('launch-ready'),null,{timeout:5000});}catch(e){console.log('PAGE ERRORS',errors);console.log(await page.locator('#fatal').allTextContents());throw e;}
for(const [width,height] of [[1380,900],[940,640],[768,512],[640,420],[640,360]]){
 await page.setViewportSize({width,height});await page.waitForTimeout(150);
 for(const sel of ['#shell','#body','#main','#scroll']){const d=await page.locator(sel).evaluate(e=>({w:e.clientWidth,sw:e.scrollWidth,h:e.clientHeight,sh:e.scrollHeight}));assert(d.sw<=d.w+1,`${sel} horizontal overflow at ${width}: ${JSON.stringify(d)}`);}
 await page.evaluate(()=>show('Performance'));await page.waitForTimeout(100);
 const card=page.locator('.tweak').first();assert(await card.isVisible());const box=await card.boundingBox();assert(box.x+box.width<=width+1,`Card clipped at ${width}`);
}
for(const edge of ['n','s','e','w','ne','nw','se','sw']){const grip=page.locator('.resize-'+edge);await grip.dispatchEvent('pointerdown',{button:0});}
assert.deepEqual(await page.evaluate(()=>resizeCalls),['n','s','e','w','ne','nw','se','sw']);assert.deepEqual(errors,[]);console.log('PASS: five viewport sizes down to 640×360, no horizontal clipping in shell/main/content, eight resize grips dispatch correctly.');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exit(1)});
