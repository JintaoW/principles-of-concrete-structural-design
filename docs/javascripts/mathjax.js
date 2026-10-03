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
    output: {
      font: "mathjax-termes"
    },
    options: {
      ignoreHtmlClass: ".*",
      processHtmlClass: "arithmatex"
    }
  };
})();

document$.subscribe(() => {
  // 字体等异步资源加载期间 typesetPromise 可能尚未就绪, 加保护
  if (window.MathJax && MathJax.typesetPromise) MathJax.typesetPromise()
});
