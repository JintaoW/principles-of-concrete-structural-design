(function () {
  // Termes 字体包自托管于站点内, 覆盖默认的 jsdelivr CDN 路径。
  // 以 mathjax.js 自身的 script src 为基准推导站点根绝对 URL,
  // 兼容 mkdocs 目录式 URL 与 RTD 的 /en/latest/ 子路径。
  var fontsUrl = new URL("../assets/mathjax/fonts", document.currentScript.src).href;
  window.MathJax = {
    loader: {
      paths: { fonts: fontsUrl }
    },
    tex: {
      inlineMath: [["\\(", "\\)"]],
      displayMath: [["\\[", "\\]"]],
      processEscapes: true,
      processEnvironments: true
    },
    startup: {
      // 关闭整页自动排版: 公式量大(ch07逾700个,全量排版约30s), 改为视口懒渲染
      typeset: false
    },
    output: {
      font: "mathjax-termes"
    },
    options: {
      ignoreHtmlClass: ".*",
      // 正则语义, 必须用|分隔(空格分隔会失配)
      // arithmatex: 构建期转换的公式; tex2jax-process: 原生HTML表格单元格(md_in_html不处理td内容)
      processHtmlClass: "arithmatex|tex2jax-process"
    }
  };
})();

// 视口懒渲染: 首屏立即排, 其余滚动到视口附近(rootMargin提前量)再排。
// 排版调用串行排队(MathJax要求), 打印前全量兜底。
// 注意: document$首次触发时MathJax可能尚未加载完, 必须等startup.promise再动手。
function whenMathJaxReady(cb) {
  if (window.MathJax && MathJax.startup && MathJax.startup.promise) {
    MathJax.startup.promise.then(cb);
  } else {
    var t = setInterval(function () {
      if (window.MathJax && MathJax.startup && MathJax.startup.promise) {
        clearInterval(t);
        MathJax.startup.promise.then(cb);
      }
    }, 100);
  }
}

document$.subscribe(function () {
  whenMathJaxReady(function () {

  function pending() {
    return Array.from(document.querySelectorAll(".arithmatex, .tex2jax-process"))
      .filter(function (el) { return !el.dataset.mjxDone; });
  }

  var targets = pending();
  if (!targets.length) return;

  var chain = Promise.resolve();
  function enqueue(els) {
    els.forEach(function (el) { el.dataset.mjxQueued = "1"; });
    chain = chain
      .then(function () { return MathJax.typesetPromise(els); })
      .then(function () { els.forEach(function (el) { el.dataset.mjxDone = "1"; }); })
      .catch(function (err) { console.error("MathJax typeset:", err); });
  }

  if (!("IntersectionObserver" in window)) {
    enqueue(targets);   // 极旧浏览器降级为全量
    return;
  }

  var io = new IntersectionObserver(function (entries) {
    var todo = entries.filter(function (e) { return e.isIntersecting; })
                      .map(function (e) { return e.target; });
    if (todo.length) { todo.forEach(function (el) { io.unobserve(el); }); enqueue(todo); }
  }, { rootMargin: "400px 0px" });
  targets.forEach(function (el) { io.observe(el); });

  // 打印/导出PDF前排版剩余全部(同步等待不可能, 尽最大努力)
  window.addEventListener("beforeprint", function () {
    var rest = pending().filter(function (el) { return !el.dataset.mjxQueued; });
    if (rest.length) enqueue(rest);
  });
  });
});
