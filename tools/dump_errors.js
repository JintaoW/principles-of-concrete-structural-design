const { chromium } = require('playwright-core');
(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage();
  for (const ch of ['ch02','ch04','ch06','ch07']) {
    await page.goto(`http://localhost:8000/${ch}/`, { waitUntil: 'load', timeout: 60000 });
    await page.waitForTimeout(7000);
    const errs = await page.evaluate(() => {
      const out = [];
      document.querySelectorAll('mjx-merror').forEach(m => {
        const c = m.closest('mjx-container');
        out.push((c ? c.textContent : '').slice(0, 100) + ' ||| ' + m.textContent.slice(0, 150));
      });
      return out;
    });
    console.log(`===== ${ch}: ${errs.length} =====`);
    [...new Set(errs)].slice(0, 12).forEach(e => console.log(' ', e.replace(/\n/g, ' ')));
  }
  await browser.close();
})().catch(e => { console.error('FAIL:', e.message); process.exit(1); });
