const { chromium } = require(process.env.PW || 'playwright');
const { pathToFileURL } = require('url');
const path = require('path');
const assert = require('assert');

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROME });
  try {
    const page = await browser.newPage({ viewport: { width: 1380, height: 900 } });
    await page.goto(pathToFileURL(path.resolve(__dirname, '../src/web/index.html')).href);
    await page.evaluate(() => {
      document.body.classList.remove('booting');
      document.getElementById('bootlayer')?.remove();
      window.testCalls = [];
      window.api = async (name, action) => {
        const status = { ok: true, name: 'Microsoft Windows 11 Pro', edition: 'Professional', version: '25H2', build: '26200', activated: !!window.testActivated };
        if (name === 'windows_status') return status;
        if (name !== 'windows_setup') return [];
        window.testCalls.push(action);
        if (action === 'activate' && window.testActivated) return { ok: true, already_activated: true, status, message: 'Windows is already activated.' };
        if (window.testFailure) return { ok: false, message: 'A Windows setup tool is already open.' };
        return { ok: true, message: 'MAS opened in a separate window.' };
      };
      pageRes();
    });
    await page.getByRole('button', { name: 'Activate Windows', exact: true }).click();
    await page.waitForFunction(() => document.getElementById('windowsSetupMessage').textContent.includes('MAS opened'));
    await page.getByRole('button', { name: 'Change Windows Version', exact: true }).click();
    assert((await page.locator('#editionCurrentName').textContent()).includes('Windows 11 Pro'));
    assert.deepStrictEqual(await page.evaluate(() => window.testCalls), ['activate']);
    await page.getByRole('button', { name: 'Open edition chooser', exact: true }).click();
    assert.deepStrictEqual(await page.evaluate(() => window.testCalls), ['activate', 'edition']);
    await page.evaluate(() => { window.testFailure = true; });
    await page.getByRole('button', { name: 'Activate Windows', exact: true }).click();
    await page.waitForFunction(() => document.getElementById('windowsSetupMessage').textContent.includes('already open'));
    assert(await page.getByRole('button', { name: 'Activate Windows', exact: true }).isEnabled());
    assert.strictEqual(await page.locator('[data-res]').count(), 3);
    await page.evaluate(() => { window.testActivated = true; window.testFailure = false; });
    await page.getByRole('button', { name: 'Activate Windows', exact: true }).click();
    await page.getByRole('heading', { name: 'Windows is already activated', exact: true }).waitFor();
    await page.getByRole('button', { name: 'OK', exact: true }).click();
    await page.getByRole('button', { name: 'Change Windows Version', exact: true }).click();
    await page.getByRole('button', { name: 'Cancel', exact: true }).click();
    await page.evaluate(() => { const message = document.getElementById('windowsSetupMessage'); message.textContent = 'Bundled from massgravel/Microsoft-Activation-Scripts · GPL-3.0'; message.style.color = 'var(--muted)'; });
    await page.screenshot({ path: path.resolve(__dirname, '../docs/windows-setup.png') });
    await page.setViewportSize({ width: 940, height: 640 });
    assert(await page.getByRole('button', { name: 'Change Windows Version', exact: true }).isVisible());
    console.log('PASS: both button routes, error feedback, retry, repair tools and minimum viewport.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
