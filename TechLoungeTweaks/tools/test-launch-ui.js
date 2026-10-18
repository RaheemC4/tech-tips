const {chromium} = require(process.env.PW || 'playwright');
const {pathToFileURL} = require('url');
const path = require('path');
const assert = require('assert');
(async () => {
  const browser = await chromium.launch({executablePath: process.env.CHROME});
  try {
    for (const reducedMotion of ['no-preference', 'reduce']) {
      const page = await browser.newPage({viewport:{width:940,height:640}, reducedMotion});
      await page.addInitScript((openUpdateDetails) => {
        window.pywebview = {api:{reveal:() => { window.nativeReveal = {loader:getComputedStyle(document.getElementById("bootlayer")).display, title:document.getElementById("ptitle").textContent}; return true; },init:() => new Promise(resolve => {
          window.finishLaunch = () => resolve({tweaks:[{key:"game_mode",name:"Game Mode",desc:"Test",category:"Performance",applied:true,locked:false,icon:"bolt"}],categories:["Performance"],admin:true,specs:{CPU:"Recent CPU"},scanning:true,open_updates:openUpdateDetails});
        })}};
      }, reducedMotion === 'reduce');
      await page.goto(pathToFileURL(path.resolve(__dirname, '../src/web/index.html')).href);
      await page.waitForFunction(() => typeof finishLaunch === 'function');
      assert(await page.locator('#bootlayer').isVisible());
      assert.strictEqual(await page.locator('#shell').evaluate(e => getComputedStyle(e).opacity), '0');
      await page.evaluate(() => {
        window.launchFrames = [];
        function sample() {
          if (document.body.classList.contains('launch-ready')) {
            launchFrames.push(Number(getComputedStyle(document.getElementById('shell')).opacity));
          }
          if (launchFrames.length < 40) requestAnimationFrame(sample);
        }
        requestAnimationFrame(sample);
        finishLaunch();
      });
      await page.waitForFunction(() => document.body.classList.contains('launch-ready'));
      // Home must be painted throughout the handoff, never an empty background.
      assert.strictEqual(await page.locator('#shell').evaluate(e => getComputedStyle(e).opacity), '1');
      await page.waitForFunction(() => window.nativeReveal);
      assert.deepStrictEqual(await page.evaluate(() => nativeReveal), {loader:'none', title:'Overview'});
      assert(!(await page.locator('#bootlayer').isVisible()));
      assert.strictEqual(await page.locator('[data-nav]').count(), 23);
      assert.strictEqual(await page.locator('#ptitle').innerText(), 'Overview');
      if (reducedMotion === 'reduce') await page.waitForFunction(() => document.getElementById('updatesPanel')?.hidden === false);
      else assert(!(await page.locator('#updatesPanel').isVisible()));
      assert((await page.locator('#specs').innerText()).includes('Recent CPU'));
      await page.waitForFunction(() => document.getElementById('scoreNum').textContent === '100');
      assert.strictEqual(await page.locator('[data-chip="Performance"]').innerText(), '1/1');
      await page.evaluate(() => py_scanned({tweaks:[{key:'game_mode',name:'Game Mode',desc:'Test',category:'Performance',applied:false,locked:false,icon:'bolt'}],categories:['Performance']}));
      await page.waitForFunction(() => document.getElementById('scoreNum').textContent === '0');
      assert((await page.evaluate(() => launchFrames)).every(opacity => opacity === 1));
      const animation = await page.locator('#shell').evaluate(e => getComputedStyle(e).animationName);
      assert.strictEqual(animation, reducedMotion === 'reduce' ? 'none' : 'launch-settle');
      await page.waitForFunction(() =>
        getComputedStyle(document.getElementById('shell')).transform === 'none');
      assert.strictEqual(await page.locator('#shell').evaluate(e => getComputedStyle(e).opacity), '1');
      assert.strictEqual(await page.locator('#shell').evaluate(e => getComputedStyle(e).transform), 'none');
      await page.close();
    }
    console.log('Launch: delayed backend, populated navigation, spring settle and reduced motion passed.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
