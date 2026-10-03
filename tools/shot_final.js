const { chromium } = require('playwright-core');
(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  // ch07 前3个独立公式 + ch06 第2个
  for (const [ch, idx, name] of [['ch07', 0, 'ch07_eq0'], ['ch07', 3, 'ch07_eq3'], ['ch06', 1, 'ch06_eq1']]) {
    await page.goto(`http://localhost:8000/${ch}/`, { waitUntil: 'load', timeout: 60000 });
    await page.waitForFunction(() => document.querySelectorAll('mjx-container').length > 20, { timeout: 30000 });
    await page.waitForTimeout(2500);
    const eqs = page.locator('div.eq');
    await eqs.nth(idx).screenshot({ path: `D:/WorkbuddyProjects/ConcreteDocs/work/shots/${name}.png` });
    console.log(name, '已截图');
  }
  await browser.close();
})().catch(e => { console.error('FAIL:', e.message); process.exit(1); });
