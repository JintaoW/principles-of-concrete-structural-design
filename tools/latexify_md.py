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
# 合并 MathType 提取结果(若有)
mt_path = ROOT / 'work' / 'extract' / f'{ch}_mt_latex.json'
if mt_path.exists():
    mt = json.loads(mt_path.read_text(encoding='utf-8'))
    data = {'chapter': ch, 'oles': data['oles'] + mt['oles']}
    print(f'合并 MathType 结果: {sum(1 for o in mt["oles"] if o[3])} 个')
body = {}  # imageN.png -> latex body
from collections import Counter




groups = {}  # name -> [latex...] 多数票
for idx, pid, media, latex in data['oles']:
    if not latex:
        continue
    raw = latex.strip()
    # sanity 检查原始形式: AxMath 输出 $...$, MathType 输出 \(...\)/\[...\]
    if not (raw.startswith('$') or raw.startswith('\\(') or raw.startswith('\\[')):
        print(f'过滤异常LaTeX: {media} <- {raw[:50]!r} (保留图片)')
        continue
    stem = media.rsplit('.', 1)[0]
    name = stem + '.png'
    if not (ROOT / 'docs' / 'images' / ch / name).exists():
        name = 'v' + stem + '.png'  # 多数章公式图带 v 前缀
    s = raw
    if s.startswith('$') and s.endswith('$'):
        s = s[1:-1].strip()
    if s.startswith('\\(') and s.endswith('\\)'):
        s = s[2:-2].strip()
    if s.startswith('\\[') and s.endswith('\\]'):
        s = s[2:-2].strip()
    if not s:
        print(f'过滤空翻译: {media} (保留图片)')
        continue
    groups.setdefault(name, []).append(s)

# MathJax 兼容性修正
for k in body:
    body[k] = re.sub(r"\^(['‘’]+)", r"^{\1}", body[k])
    body[k] = body[k].replace(r"\kern-\nulldelimiterspace", r"\kern-1.2pt")

for name, lats in groups.items():
    if len(set(lats)) > 1:
        top = Counter(lats).most_common(1)[0]
        print(f'警告: {name} LaTeX不一致({len(lats)}个), 取多数票({top[1]}票)')
        body[name] = top[0]
    else:
        body[name] = lats[0]

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
