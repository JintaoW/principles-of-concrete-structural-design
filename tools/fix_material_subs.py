# -*- coding: utf-8 -*-
r"""材料/受力类下标正体化（用户指定铁律补丁）：
下标 c(混凝土)/s(钢筋)/t(受拉)/y(屈服) 及 py/yv/ck/tk/yk/pyk/stk/ptk 一律正体，基符号保持斜体。
- 公式：_{c}/_{s}/_{y} 与裸 _c/_s/_t/_y → _{\\mathrm{X}}（裸形式后跟字母=新基符号，一并转换）
- 正文：*X<sub>c</sub>* 外层em拆分；<sub><em>c</em></sub> 内层em剥离
序号 i/j 与轴号 x/y 复合下标（_{\mathrm{c}i}、G_{jk} 等）不受影响。
"""
import glob, re

TARGETS = 'csty'

def fix_math(content):
    n = 0
    def repl(m):
        nonlocal n
        n += 1
        return '_{\\mathrm{' + m.group(1) + '}}'
    # 花括号单字母 _{c}
    content = re.sub(r'_\{([' + TARGETS + r'])\}', repl, content)
    # 裸单字母 _c（后跟字母=乘积连写的新基，同样转换；不排除字母）
    content = re.sub(r'_([' + TARGETS + r'])(?!\{)', repl, content)
    return content, n

def fix_text(content):
    n = 0
    # 1) sub 内层 em 剥离（*A*<sub><em>s</em></sub> 或 *A<sub><em>s</em></sub>*）
    def inner(m):
        nonlocal n
        n += 1
        return '<sub>' + m.group(1) + '</sub>'
    content = re.sub(r'<sub><em>([' + TARGETS + r'])</em></sub>', inner, content)
    # 2) 外层 em 包裹拆分（*X<sub>c</sub>* → *X*<sub>c</sub>）
    def outer(m):
        nonlocal n
        n += 1
        return '*' + m.group(1) + '*<sub>' + m.group(2) + '</sub>'
    content = re.sub(
        r'\*([A-Za-z]+(?:<sup>[^<]*</sup>)?)<sub>([' + TARGETS + r'])</sub>\*',
        outer, content)
    return content, n

total_m = total_t = 0
for path in sorted(glob.glob('docs/ch0*.md')) + ['docs/index.md']:
    content = open(path, encoding='utf-8').read()
    content2, nm = fix_math(content)
    content2, nt = fix_text(content2)
    if nm or nt:
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write(content2)
    print(f'{path}: math={nm} text={nt}')
    total_m += nm
    total_t += nt
print(f'TOTAL math={total_m} text={total_t}')
