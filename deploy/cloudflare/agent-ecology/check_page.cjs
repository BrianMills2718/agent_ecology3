// Browser check for the public replay: page errors, sideways scroll at phone width,
// and a styled tooltip on every control (hover each one, read the bubble).
// Usage: node check_page.cjs <base-url ending in /agent-ecology/> [screenshot-prefix]
const { chromium } = require('playwright');
const base = process.argv[2];
const shot = process.argv[3] || 'replay';
const CONTROLS = 'button, a, select, input, summary, [tabindex="0"], .gm-cell, .gm-row, .gm-col';

async function tooltips(page, tipSelector) {
  const els = await page.$$(CONTROLS);
  let checked = 0, offscreen = 0, missing = [];
  for (const el of els) {
    if (!(await el.isVisible())) continue;
    // A control pushed off the side of the page (a closed side panel) cannot be hovered; count it apart.
    const sideways = await el.evaluate(e => { const r = e.getBoundingClientRect();
      return getComputedStyle(e).position !== 'static' || e.closest('[class*=inspector]') ? (r.left >= window.innerWidth || r.right <= 0) : false; });
    if (sideways) { offscreen++; continue; }
    await el.hover({ force: true });
    await page.waitForTimeout(40);
    const text = await page.$eval(tipSelector, t => (getComputedStyle(t).display !== 'none' ? t.textContent.trim() : ''));
    checked++;
    if (!text) missing.push(await el.evaluate(e => e.outerHTML.slice(0, 80)));
  }
  return { checked, offscreen, missing: missing.length, examples: missing.slice(0, 5) };
}

(async () => {
  const browser = await chromium.launch();
  const result = {};
  for (const [label, path, tipSel] of [['index', '', '#tip'], ['living', 'living.html', '#ae3Tip']]) {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const errors = [];
    page.on('pageerror', e => errors.push(String(e)));
    page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
    const resp = await page.goto(base + path, { waitUntil: 'networkidle', timeout: 120000 });
    await page.waitForTimeout(1500);
    const r = { status: resp.status() };
    if (label === 'index') {
      await page.click('#endButton');
      r.feedRows = await page.$$eval('#feed .row', x => x.length);
      r.feedText = await page.$eval('#feedCount', x => x.textContent);
      r.feedTips = await tooltips(page, tipSel);
      await page.screenshot({ path: `${shot}_feed.png`, fullPage: false });
      await page.click('#tabMatrix');
      await page.waitForTimeout(300);
      r.matrixCells = await page.$$eval('#matrix .gm-cell', x => x.length);
      r.matrixTips = await tooltips(page, tipSel);
      await page.hover('td.gm-reuse');
      await page.waitForTimeout(150);
      await page.screenshot({ path: `${shot}_matrix.png`, fullPage: false });
    } else {
      r.label = (await page.content()).includes('Rendered with the World Substrate living view; outcomes from agent_ecology3.');
      r.tips = await tooltips(page, tipSel);
      await page.screenshot({ path: `${shot}_living.png`, fullPage: false });
    }
    // Phone width: no sideways page scroll.
    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForTimeout(400);
    r.phoneOverflowPx = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    await page.screenshot({ path: `${shot}_${label}_phone.png`, fullPage: false });
    r.pageErrors = errors;
    result[label] = r;
    await page.close();
  }
  await browser.close();
  console.log(JSON.stringify(result, null, 1));
  const bad = Object.values(result).some(r => r.status !== 200 || r.pageErrors.length || r.phoneOverflowPx > 0 ||
    (r.feedTips && r.feedTips.missing) || (r.matrixTips && r.matrixTips.missing) || (r.tips && r.tips.missing) || r.label === false);
  console.log(bad ? 'BROWSER CHECK: FAILED' : 'BROWSER CHECK: PASSED');
  process.exit(bad ? 1 : 0);
})();
