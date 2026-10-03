const { chromium } = require('playwright-core');
(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  await page.goto('http://localhost:8000/ch02/', { waitUntil: 'load', timeout: 60000 });
  await page.waitForFunction(() => document.querySelectorAll('mjx-container').length > 50, { timeout: 30000 });
  await page.waitForTimeout(2000);
  const eqs = page.locator('div.eq');
  const n = await eqs.count();
  console.log('eq div总数:', n);
  for (let i = 0; i < n; i++) {
    await eqs.nth(i).screenshot({ path: `D:/WorkbuddyProjects/ConcreteDocs/work/shots/eq_${i}.png` });
  }
  console.log('已截图', n, '个独立公式');
  await browser.close();
})().catch(e => { console.error('FAIL:', e.message); process.exit(1); });
