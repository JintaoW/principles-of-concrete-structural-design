# -*- coding: utf-8 -*-
"""Markdown 排版后处理（9 章通用，幂等可重跑）

功能:
  A. 独立公式段重写为 HTML 块: 公式严格居中、编号贴右对齐
     - 识别规则: 整段仅由图片引用 + 可选尾部编号构成（无其他文字）
     - 行内公式（图片与文字混排）保持原样, 由 CSS 基线对齐
  B. 图注段(预留, 批量阶段细化): 紧跟图片段、以"图 N-N"开头的行 -> 居中图注

用法:
  python layout.py docs/ch01.md docs/ch02.md ...
"""
import re
import sys
from pathlib import Path

# 公式段: 整行 = 一个或多个 ![](path){width=N} + 可选尾部编号
IMG = r'!\[\]\(([^)]+)\)(?:\{width=(\d+)\})?'
NO_TAIL = r'[（(]?[\d\s,\-–、．.]+[）)]?'   # 如 (2-6) 或 2-9, 2-10
EQ_LINE = re.compile(rf'^(?P<imgs>(?:\s*{IMG})+)\s*(?P<no>{NO_TAIL})?\s*$')

# Word 交叉引用 -> Pandoc 页内链接 [text](#anchor)。
# 讲义中这些仅为书签跳转（网页中由侧边目录与搜索承担导航），
# 且锚点在 MkDocs slugify 后大多失效成断链、渲染为蓝色，与"全黑"要求冲突。
# 处理: 一律还原为纯文本。
# 链接文本可含转义方括号（如 [设计可靠指标\[*β*\]](#anchor)）
LINK = re.compile(r'\[((?:\\\]|[^\]])+)\]\(#[^)]*\)')

def strip_links(text: str):
    n = len(LINK.findall(text))
    return LINK.sub(r'\1', text), n

# Pandoc 会把 docx 中带左缩进的段落误判为引用块(> ...)，Material 将其渲染为
# 灰色文字+左侧灰色竖线，形似审阅批注，与"全黑、无审阅痕迹"的要求冲突。
# 讲义中不存在真正的引文语义，一律还原为普通段落（'> ' 去前缀，'>' 行转空行）。
def strip_blockquotes(text: str):
    out, n, in_fence = [], 0, False
    for line in text.split('\n'):
        if line.lstrip().startswith('```'):
            in_fence = not in_fence
            out.append(line)
            continue
        if not in_fence and line.startswith('>'):
            s = line[1:]
            if s.startswith(' '):
                s = s[1:]
            if s.strip():
                n += 1
            out.append(s)
        else:
            out.append(line)
    return '\n'.join(out), n

# 图片路径规范化: 页面 URL 为 /chNN/（目录式），相对路径 images/ 会被解析为
# /chNN/images/... 导致 404。统一改站根绝对路径 /images/。
def fix_img_paths(text: str):
    return (text.replace('](images/', '](/images/')
                .replace('src="images/', 'src="/images/'))

# 表名/图名题注: 行首"表2-1 ×××"（或斜体"图2-1 ×××"）整行 → 居中题注
CAPTION_TBL = re.compile(r'^表\s?\d+[-–]\d+\s+\S.{0,80}$')
CAPTION_FIG = re.compile(r'^\*?图\s?\d+[-–]\d+\s+\S.{0,80}\*?$')

# 独立插图段: 整行仅由一个或多个 <img ...> 组成 → 居中 .fig
HTML_IMG = r'<img src="[^"]+"[^>]*?/?>'
FIG_LINE = re.compile(rf'^\s*(?:{HTML_IMG}\s*)+$')

def convert_fig(line: str):
    if not FIG_LINE.match(line):
        return None
    return '<div class="fig">\n' + line.strip() + '\n</div>'

def convert_line(line: str) -> str:
    m = EQ_LINE.match(line.strip())
    if not m:
        return None
    imgs = []
    for src, w in re.findall(IMG, m.group('imgs')):
        if not src.startswith('/'):
            src = '/' + src.lstrip('/')
        style = f' style="width:{w}px"' if w else ''
        imgs.append(f'<img src="{src}"{style} alt="">')
    no = (m.group('no') or '').strip()
    no_html = f'<span class="eq-no">{no}</span>' if no else ''
    return (
        '<div class="eq">\n'
        f'  <span class="eq-body">{"".join(imgs)}</span>{no_html}\n'
        '</div>'
    )

def process(md_path: Path) -> None:
    text = md_path.read_text(encoding='utf-8')
    text, n_link = strip_links(text)
    text, n_bq = strip_blockquotes(text)
    text = fix_img_paths(text)
    # ---- 表格包裹(逐块幂等): md 管道表 与 Pandoc 原生 HTML 表(复杂表格/合并单元格) ----
    n_wrap = 0
    lines = text.split('\n')
    out = []
    i = 0
    while i < len(lines):
        s = lines[i].lstrip()
        is_pipe = s.startswith('|')
        is_html = s.startswith('<table')
        if not (is_pipe or is_html):
            out.append(lines[i])
            i += 1
            continue
        j = i
        if is_pipe:
            while j < len(lines) and lines[j].lstrip().startswith('|'):
                j += 1
        else:
            while j < len(lines) and '</table>' not in lines[j]:
                j += 1
            j = min(j + 1, len(lines))
        block = lines[i:j]
        # 已被包裹的块(前一输出行为 wrap 开标签)直接放行
        if out and out[-1].strip() == '<div class="tbl-wrap" markdown="1">':
            out.extend(block)
        else:
            out.append('<div class="tbl-wrap" markdown="1">')
            out.extend(block)
            out.append('</div>')
            n_wrap += 1
        i = j
    text = '\n'.join(out)
    out_lines, n_eq, n_cap, n_fig = [], 0, 0, 0
    inside_block = 0   # 处于 <div class="eq/fig/tbl-wrap"> 块内时整块直通(幂等关键)
    for line in text.split('\n'):
        ls = line.lstrip()
        if inside_block > 0:
            inside_block += ls.count('<div') - ls.count('</div>')
            out_lines.append(line)
            continue
        if ls.startswith(('<div class="eq">', '<div class="tbl-wrap"', '<div class="fig">')):
            inside_block += ls.count('<div') - ls.count('</div>')
            out_lines.append(line)
            continue
        fig = convert_fig(line)
        if fig:
            out_lines.append(fig)
            n_fig += 1
            continue
        html = convert_line(line)
        if html:
            out_lines.append(html)
            n_eq += 1
            continue
        s = line.strip()
        if CAPTION_TBL.match(s):
            out_lines.append(f'<p class="tbl-caption" markdown="1">{s}</p>')
            n_cap += 1
            continue
        if CAPTION_FIG.match(s) and s.startswith('*'):
            out_lines.append(f'<p class="fig-caption" markdown="1">{s}</p>')
            n_cap += 1
            continue
        out_lines.append(line)
    md_path.write_text('\n'.join(out_lines), encoding='utf-8')
    print(f'[layout] {md_path.name}: 公式段 {n_eq} 处, 题注 {n_cap} 处, 插图段 {n_fig} 处, 链接 {n_link} 处, 引用块 {n_bq} 处, 表格包裹 {n_wrap} 个')

if __name__ == '__main__':
    for p in sys.argv[1:]:
        process(Path(p))
