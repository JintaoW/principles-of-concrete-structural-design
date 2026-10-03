// 全书体检 v2：裸TeX残留 + 渲染错误 + 空容器 + 超长公式宽度测量
const { chromium } = require('playwright-core');
(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const chapters = ['index','ch01','ch02','ch03','ch04','ch05','ch06','ch07','ch08','ch09'];
  const texPat = /\\(color|frac|left|right|sum|alpha|beta|rho|sigma|tau|varphi|xi|omega|leqslant|geqslant|displaystyle|text|rm|mathord|vphantom|kern|mathrm)/;
  let siteClean = true;
  for (const ch of chapters) {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await page.goto(`http://localhost:8000/${ch === 'index' ? '' : ch + '/'}`, { waitUntil: 'load', timeout: 60000 });
    await page.waitForTimeout(3000);
    // 懒渲染适配: 扫描前强制全量排版(等待MathJax就绪后清空懒渲染标记并全量排)
    await page.evaluate(async () => {
      const ready = window.MathJax && MathJax.startup && MathJax.startup.promise
        ? await MathJax.startup.promise
        : null;
      document.querySelectorAll('[data-mjx-done]').forEach(el => { delete el.dataset.mjxDone; });
      if (window.MathJax && MathJax.typesetPromise) await MathJax.typesetPromise();
    });
    const res = await page.evaluate((pat) => {
      const out = { raws: [], merror: 0, empty: 0, longEqs: [] };
      const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      while (walk.nextNode()) {
        const t = walk.currentNode.textContent;
        if (t.includes('\\') && new RegExp(pat).test(t) &&
            !walk.currentNode.parentElement.closest('mjx-container') &&
            !walk.currentNode.parentElement.closest('.md-ellipsis')) // 目录栏不算
          out.raws.push(t.trim().slice(0, 90));
      }
      document.querySelectorAll('mjx-merror').forEach(() => out.merror++);
      document.querySelectorAll('mjx-container').forEach(c => { if (!c.textContent.trim()) out.empty++; });
      // 宽度测量：正文可用宽度 vs 每个独立公式宽度
      const article = document.querySelector('article');
      if (article) {
        const avail = article.clientWidth - 48; // 左右padding近似
        document.querySelectorAll('div.eq').forEach(d => {
          const body = d.querySelector('.eq-body');
          if (!body) return;
          const mc = body.querySelector('mjx-container');
          const w = mc ? mc.getBoundingClientRect().width : body.getBoundingClientRect().width;
          if (w > avail) out.longEqs.push({ w: Math.round(w), avail, no: (d.querySelector('.eq-no')||{}).textContent || '', text: (body.textContent||'').trim().slice(0, 60) });
        });
        out.longEqs.sort((a, b) => b.w - a.w);
      }
      return out;
    }, texPat.source);
    const bad = res.raws.length || res.merror || res.empty;
    if (bad) siteClean = false;
    console.log(`${ch}: 错误${res.merror} 空${res.empty} 裸TeX${res.raws.length} 超长公式${res.longEqs.length}${bad ? ' <<< 异常' : ''}`);
    [...new Set(res.raws)].slice(0, 4).forEach(r => console.log('   裸>', r.replace(/\n/g, ' ')));
    res.longEqs.slice(0, 8).forEach(e => console.log(`   宽>${e.w}px/${e.avail}px ${e.no} ${e.text.replace(/\n/g, ' ')}`));
    await page.close();
  }
  await browser.close();
  console.log(siteClean ? '== 渲染层面全书干净 ==' : '== 渲染层面仍有问题 ==');
})().catch(e => { console.error('FAIL:', e.message); process.exit(1); });
