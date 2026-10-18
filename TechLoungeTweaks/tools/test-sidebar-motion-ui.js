const {chromium} = require(process.env.PW || 'playwright');
const {pathToFileURL} = require('url');
const path = require('path');
const assert = require('assert');
(async () => {
  const browser = await chromium.launch({executablePath:process.env.CHROME});
  try {
    const page = await browser.newPage({viewport:{width:940,height:640}});
    page.on('pageerror',error=>console.error(error.message));
    await page.addInitScript(() => {
      window.pywebview = {api:{init:async () => {
        if(document.readyState!=='complete')await new Promise(resolve=>window.addEventListener('load',resolve,{once:true}));
        return {tweaks:[],categories:[],admin:true,specs:{},scanning:true};
      }}};
    });
    await page.goto(pathToFileURL(path.resolve(__dirname,'../src/web/index.html')).href);
    await page.waitForFunction(() => document.body.classList.contains('launch-ready'));
    await page.evaluate(async () => {await Promise.all(document.querySelector('#navlist').getAnimations({subtree:true}).map(a => a.finished.catch(() => {})));});
    const samples = await page.evaluate(() => {
      setNavGroup('TWEAKS',true);
      const items = document.querySelector('#nav-TWEAKS');
      const animation = items.getAnimations()[0];
      animation.pause();
      return [0,65,130,195,260].map(time => {
        animation.currentTime=time;
        return {height:items.getBoundingClientRect().height,below:document.querySelector('[data-navgroup="SYSTEM"]').getBoundingClientRect().top};
      });
    });
    assert(samples[1].height>samples[0].height && samples[1].height<samples[4].height);
    assert(samples[2].height>samples[1].height && samples[2].height<samples[4].height);
    assert(samples[2].below>samples[1].below,'Following categories must move with the expansion');
    const reversal = await page.evaluate(() => {
      const items=document.querySelector('#nav-TWEAKS');
      items.getAnimations()[0].currentTime=100;
      const before=items.getBoundingClientRect().height;
      setNavGroup('TWEAKS',false);
      const after=items.getBoundingClientRect().height;
      return {before,after,inert:items.inert};
    });
    assert(Math.abs(reversal.before-reversal.after)<1,'Rapid reversal must not jump');
    assert(reversal.inert,'Closing links must leave keyboard navigation immediately');
    await page.evaluate(async () => {
      setNavGroup('SYSTEM',true);setNavGroup('TOOLS',true);setNavGroup('SYSTEM',true);
      await Promise.all(document.querySelector('#navlist').getAnimations({subtree:true}).map(a=>a.finished.catch(()=>{})));
    });
    assert(await page.locator('#nav-TWEAKS').evaluate(e=>e.hidden));
    assert(await page.locator('#nav-TOOLS').evaluate(e=>e.hidden));
    assert(!(await page.locator('#nav-SYSTEM').evaluate(e=>e.hidden)));
    await page.locator('[data-nav="System Info"]').focus();
    await page.evaluate(()=>setNavGroup('SYSTEM',false));
    assert.strictEqual(await page.evaluate(()=>document.activeElement.dataset.navgroupToggle),'SYSTEM');
    await page.emulateMedia({reducedMotion:'reduce'});
    await page.evaluate(()=>setNavGroup('TOOLS',true));
    assert.strictEqual(await page.locator('#nav-TOOLS').evaluate(e=>e.getAnimations().length),0);
    assert(!(await page.locator('#nav-TOOLS').evaluate(e=>e.hidden)));
    assert(await page.locator('#nav-SYSTEM').evaluate(e=>e.hidden));
    console.log('PASS: progressive category expansion, following-group movement, interruption, focus and reduced motion.');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exit(1);});
