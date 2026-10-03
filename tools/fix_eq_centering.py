# -*- coding: utf-8 -*-
"""把孤立的「行内公式+编号」段落转换为 div.eq 居中公式块。
匹配: ^$FORMULA$ (N-NNa?)$  →  <div class="eq">...</div>
带文字前缀/后缀的混合行不动。幂等：已是 div 的行不会匹配。
"""
import re, sys, glob

PAT = re.compile(r'^\$([^$]+)\$\s*\((\d+-\d+[a-z]?)\)\s*$')

TPL = (
    '<div class="eq">\n'
    '  <span class="eq-body"><span class="arithmatex">'
    '\\( \\displaystyle {formula} \\)</span></span>'
    '<span class="eq-no">({num})</span>\n'
    '</div>'
)

total = 0
for path in sorted(glob.glob('docs/ch0*.md')):
    with open(path, encoding='utf-8') as f:
        lines = f.read().split('\n')
    changed = 0
    for i, line in enumerate(lines):
        m = PAT.match(line.strip())
        if m:
            lines[i] = TPL.format(formula=m.group(1).strip(), num=m.group(2))
            changed += 1
    if changed:
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write('\n'.join(lines))
        print(f'{path}: {changed} converted')
        total += changed
print('TOTAL:', total)
