const { chromium } = require('playwright-core');
(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  let totalContainers = 0, totalErrors = 0;
  for (const ch of ['ch02','ch03','ch04','ch05','ch06','ch07','ch08','ch09']) {
    const errors = [];
    page.removeAllListeners('console');
    page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text().slice(0, 120)); });
    await page.goto(`http://localhost:8000/${ch}/`, { waitUntil: 'load', timeout: 60000 });
    try {
      await page.waitForFunction(() => window.MathJax && MathJax.startup && MathJax.startup.document && MathJax.startup.document.state() >= 10, { timeout: 30000 });
    } catch (e) { /* fallback wait */ await page.waitForTimeout(6000); }
    await page.waitForTimeout(1500);
    const r = await page.evaluate(() => {
      const c = document.querySelectorAll('mjx-container').length;
      const err = document.querySelectorAll('mjx-merror, .MathJax_Error').length;
      return { c, err };
    });
    totalContainers += r.c; totalErrors += r.err;
    const jsErr = errors.filter(e => !e.includes('favicon')).length;
    console.log(`${ch}: mjx容器=${r.c} 渲染错误=${r.err} JS错误=${jsErr}`);
    if (jsErr) errors.slice(0, 3).forEach(e => console.log('   ', e));
  }
  console.log(`\n合计: ${totalContainers} 个公式容器, ${totalErrors} 个渲染错误`);
  await browser.close();
})().catch(e => { console.error('FAIL:', e.message); process.exit(1); });
