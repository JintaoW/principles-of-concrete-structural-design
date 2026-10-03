# -*- coding: utf-8 -*-
"""把正文中的 Pandoc 风格转义 \\< 与 \\> 改为 HTML 实体。

根因：Pandoc 生成 md 时把正文 < 和 > 转义为 \\< / \\>（pandoc 合法），
但 MkDocs 用的 Python-Markdown 不支持 \\<（ESCAPED_CHARS 不含 '<'），
导致网页上斜杠裸露。\\> 恰好被支持所以只显示了 < 左边的斜杠。
修复后两者统一用 HTML 实体，任何渲染器都稳定。
只处理数学区间（$...$ 单行、\\(...\\)、\\[...\\]、arithmatex span）之外的部分。
"""
import re
import glob

MATH_PROTECT = re.compile(
    r'\$[^$\n]+\$'                # $...$ 单行
    r'|\\\((?:.|\n)*?\\\)'        # \( ... \) 可跨行
    r'|\\\[(?:.|\n)*?\\\]'        # \[ ... \] 可跨行
)

PAT = re.compile(r'\\([<>])')

total = 0
for path in sorted(glob.glob('docs/ch0*.md')) + ['docs/index.md']:
    content = open(path, encoding='utf-8').read()
    out, last, n = [], 0, 0
    for m in MATH_PROTECT.finditer(content):
        seg = content[last:m.start()]
        seg, k = PAT.subn(lambda mm: '&lt;' if mm.group(1) == '<' else '&gt;', seg)
        n += k
        out.append(seg)
        out.append(m.group(0))
        last = m.end()
    seg = content[last:]
    seg, k = PAT.subn(lambda mm: '&lt;' if mm.group(1) == '<' else '&gt;', seg)
    n += k
    out.append(seg)
    new = ''.join(out)
    if new != content:
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write(new)
    print(f'{path}: {n} 处')
    total += n
print('TOTAL:', total)
