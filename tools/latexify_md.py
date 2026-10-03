# -*- coding: utf-8 -*-
"""把 docs/<ch>.md 中的 AxMath 公式图片替换为 LaTeX 文本。

- 独立公式（eq div 内 <img ...>）→ <span class="arithmatex">\\( \\displaystyle ... \\)</span>
- 行内公式（![](...){width=N}）→ $...$
- MathType(DSMT4) 图片（不在 latex 映射中的）保持不变
用法: python latexify_md.py ch02
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ch = sys.argv[1] if len(sys.argv) > 1 else 'ch02'

data = json.loads((ROOT / 'work' / 'extract' / f'{ch}_latex.json').read_text(encoding='utf-8'))
body = {}  # imageN.png -> latex body
for idx, pid, media, latex in data['oles']:
    if not latex:
        continue
    name = media.rsplit('.', 1)[0] + '.png'
    s = latex.strip()
    if s.startswith('$') and s.endswith('$'):
        s = s[1:-1].strip()
    if name in body and body[name] != s:
        print(f'警告: {name} LaTeX不一致')
    body[name] = s

md_path = ROOT / 'docs' / f'{ch}.md'
text = md_path.read_text(encoding='utf-8')
pre = text
counts = {'disp': 0, 'inline': 0}


def repl_disp(m):
    name = m.group(1) + '.png'
    if name not in body:
        return m.group(0)
    counts['disp'] += 1
    return '<span class="arithmatex">\\( \\displaystyle ' + body[name] + ' \\)</span>'


def repl_inl(m):
    name = m.group(1) + '.png'
    if name not in body:
        return m.group(0)
    counts['inline'] += 1
    return '$' + body[name] + '$'


text = re.sub(r'<img src="/images/' + ch + r'/([^"/]+?)\.png" style="width:\d+px" alt="">', repl_disp, text)
text = re.sub(r'!\[\]\(/images/' + ch + r'/([^"/]+?)\.png\)\{width=\d+\}', repl_inl, text)

md_path.write_text(text, encoding='utf-8')
print(f"独立公式替换 {counts['disp']} 处, 行内公式替换 {counts['inline']} 处")

# 对账: 残留引用
import collections
left = collections.Counter(re.findall(r'/images/' + ch + r'/([^)"]+?\.png)', text))
ax_set = set(body)
residual_ax = {k: v for k, v in left.items() if k in ax_set}
print('残留的AxMath图片引用(应为0):', residual_ax)
kept = {k: v for k, v in left.items() if k not in ax_set}
print(f'保留为图片的引用(MathType等): {sum(kept.values)}' if False else f'保留为图片的引用(MathType等): {len(kept)}种/{sum(kept.values())}处: {sorted(kept)}')
