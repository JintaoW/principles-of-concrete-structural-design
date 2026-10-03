# -*- coding: utf-8 -*-
r"""修复三类公式HTML/Markdown问题（严格作用域版）：
A. 被空行切断的 $...$ 公式段落 → 合并为单行
   条件：当前块 $ 计数为奇数，且下一块以续接片段开头（' {'、'\'、'{'）
B. 数学式内部 '<字母' → '&lt;字母'（防浏览器解析成HTML标签）
   仅作用于 $...$ 与 \( ... \) 区间，绝不触碰HTML标签
C. 标题行(以#开头)内 $\sigma _{lN}$ → *σ*<sub>lN</sub>，正文不动
幂等：A 平衡后不动；B 替换后模式消失；C 同理。
"""
import re, glob

MATH_SPAN_RE = re.compile(r'(\$[^$\n]+\$|\\\(.+?\\\))')
HEADING_MATH_RE = re.compile(r"\$\\sigma _\{l(\d)\}(\^\{'\})?\$")
CONTINUATION_START = re.compile(r"^\s*(\{|\\|&|\})")

def fix_merge(content, path, stats):
    blocks = content.split('\n\n')
    out = []
    i = 0
    merges = 0
    while i < len(blocks):
        b = blocks[i]
        while (b.count('$') % 2 == 1 and i + 1 < len(blocks)
               and CONTINUATION_START.match(blocks[i + 1])):
            i += 1
            b = b + ' ' + blocks[i]
            merges += 1
        out.append(b)
        i += 1
    if merges:
        stats.setdefault('merged', []).append(f'{path}: {merges} joins')
    return '\n\n'.join(out)

def fix_lt(content, path, stats):
    count = 0
    def math_fix(m):
        nonlocal count
        span = m.group(0)
        new = re.sub(r'<(?=[A-Za-z])', '&lt;', span)
        if new != span:
            count += 1
        return new
    content = MATH_SPAN_RE.sub(math_fix, content)
    if count:
        stats.setdefault('lt', []).append(f'{path}: {count} spans')
    return content

def fix_heading(content, path, stats):
    n = 0
    def line_fix(line):
        nonlocal n
        if line.startswith('#'):
            def repl(m):
                nonlocal n
                n += 1
                if m.group(2):
                    return f"*σ*<sup>’</sup><sub>l{m.group(1)}</sub>"
                return f"*σ*<sub>l{m.group(1)}</sub>"
            return HEADING_MATH_RE.sub(repl, line)
        return line
    content = '\n'.join(line_fix(l) for l in content.split('\n'))
    if n:
        stats.setdefault('heading', []).append(f'{path}: {n} in headings')
    return content

total_stats = {}
for path in sorted(glob.glob('docs/ch0*.md')):
    content = open(path, encoding='utf-8').read()
    stats = {}
    content = fix_merge(content, path, stats)
    content = fix_lt(content, path, stats)
    content = fix_heading(content, path, stats)
    if stats:
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write(content)
    for k, v in stats.items():
        for item in v:
            print(f'[{k}] {item}')
print('done')
