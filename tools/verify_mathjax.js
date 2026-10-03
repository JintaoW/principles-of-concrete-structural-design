// MathJax 渲染验证: 打开ch02页, 检查编译错误, 截图关键区域
const { chromium } = require('playwright-core');
(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const consoleMsgs = [];
  page.on('console', m => consoleMsgs.push(m.type() + ': ' + m.text().slice(0, 150)));
  await page.goto('http://localhost:8000/ch02/', { waitUntil: 'load', timeout: 60000 });
  // 等MathJax完成
  await page.waitForFunction(() => window.MathJax && window.MathJax.startup && window.MathJax.startup.document && window.MathJax.startup.document.mathdone === true, { timeout: 30000 }).catch(() => console.log('mathdone标志等待超时(继续检查)'));
  await page.waitForTimeout(1500);
  const stats = await page.evaluate(() => ({
    containers: document.querySelectorAll('mjx-container').length,
    errors: document.querySelectorAll('mjx-merror, .MathJax_Error, mjx-assistive-mml [data-mjx-error]').length,
    errorTexts: [...document.querySelectorAll('[data-mjx-error]')].slice(0, 10).map(e => e.getAttribute('data-mjx-error')),
    arithmatex: document.querySelectorAll('.arithmatex').length,
  }));
  console.log('渲染统计:', JSON.stringify(stats, null, 1));
  console.log('控制台消息数:', consoleMsgs.length);
  consoleMsgs.slice(0, 8).forEach(m => console.log('  ', m));
  // 截图: 第一个独立公式(eq div)与行内公式区域
  const eq = page.locator('div.eq').first();
  if (await eq.count()) { await eq.screenshot({ path: 'D:/WorkbuddyProjects/ConcreteDocs/work/shots/eq_display.png' }); console.log('已截图: eq_display.png'); }
  const inline = page.locator('mjx-container').nth(3);
  const inlineArea = page.locator('p', { has: page.locator('mjx-container') }).first();
  await inlineArea.screenshot({ path: 'D:/WorkbuddyProjects/ConcreteDocs/work/shots/eq_inline.png' });
  console.log('已截图: eq_inline.png');
  await browser.close();
})().catch(e => { console.error('FAIL:', e.message); process.exit(1); });
