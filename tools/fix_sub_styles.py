# -*- coding: utf-8 -*-
"""全书下标样式铁律清洗：
Rule A: 单字母下标 → 斜体
Rule B: 多字母缩写下标 → 正体
例外: 序号 i/j 与轴号 x/y/z 保持斜体（ik/jk/ti/si/0i 混合内容按字母分别处理）
     ix/iy/ux/uy/u0 整体保持斜体（轴号复合量）
同时处理正文（HTML sub）与公式（TeX _{...} → \\mathrm{}）。
"""
import glob
import re

MATH = re.compile(r'\$[^$\n]+\$|\\\((?:.|\n)*?\\\)|\\\[(?:.|\n)*?\\\]')

# 单字母+数字等：字母斜体；多字母：正体；混合例外按映射
MIXED_MAP = {          # 多字母但含序号字母 → 字母级处理
    '0i': '0<em>i</em>',
    'ik': '<em>i</em>k',
    'jk': '<em>j</em>k',
    'ti': 't<em>i</em>',
    'si': 's<em>i</em>',
}
KEEP = {'ix', 'iy', 'ux', 'uy', 'u0'}   # 轴号/复合量整体斜体，不动


def math_fix(content):
    """公式侧：whitelist 下标 \\mathrm 化。返回 (content, 次数)。"""
    FULL = {'con', 'cor', 'cr', 'cs', 'cu', 'cv', 'cc', 'eq', 'ns', 'pc', 'pcr',
            'pe', 'po', 'py', 'ptk', 'pyk', 'sb', 'sh', 'sq', 'sso', 'ss0', 'ss1',
            'st1', 'stl', 'sv', 'sv1', 'te', 'tf', 'tk', 'tr', 'tw', 'yh', 'yv',
            'Rd', 'RE', 'Es', 'dst', 'stb'}
    PARTIAL = {'ci': '\\mathrm{c}i', 'qi': '\\mathrm{q}i', 'qj': '\\mathrm{q}j',
               'ti': '\\mathrm{t}i', 'si': '\\mathrm{s}i', 'pci': '\\mathrm{pc}i',
               'ik': 'i\\mathrm{k}', 'jk': 'j\\mathrm{k}'}
    n = 0

    def repl(m):
        nonlocal n
        inner = m.group(1).strip()
        if '\\mathrm' in inner:
            return m.group(0)
        if inner in FULL:
            n += 1
            return '_{\\mathrm{' + inner + '}}'
        if inner in PARTIAL:
            n += 1
            return '_{' + PARTIAL[inner] + '}'
        return m.group(0)

    content = re.sub(r'_\{([^{}]*)\}', repl, content)
    # 嵌套特例 S_{Q_ik} / S_{Q_jk}
    for old, new in [('_{Q_ik}', '_{Q_{i\\mathrm{k}}}'), ('_{Q_jk}', '_{Q_{j\\mathrm{k}}}')]:
        c = content.count(old)
        if c:
            content = content.replace(old, new)
            n += c
    return content, n


TAG_RE = re.compile(r'<[^>]+>')
SUB_RE = re.compile(r'<sub>([^<]*)</sub>')


def sub_fix_line(line):
    """一行内的 <sub> 修复。返回 (line, 次数)。"""
    n = 0
    for _ in range(60):  # 迭代至收敛（em 分裂会改变奇偶）
        m = SUB_RE.search(line)
        fixed = False
        while m:
            content = m.group(1)
            if '<em>' in content or not re.search(r'[A-Za-z]', content):
                m = SUB_RE.search(line, m.end())
                continue
            letters = re.findall(r'[A-Za-z]', content)
            core = content.strip()
            if core in KEEP:
                m = SUB_RE.search(line, m.end())
                continue
            in_em = in_em_at(line, m.start())
            if len(letters) == 1:
                if in_em:
                    m = SUB_RE.search(line, m.end())
                    continue  # 已斜体
                new_content = re.sub(r'([A-Za-z])', r'<em>\1</em>', core, count=1)
                line = line[:m.start()] + '<sub>' + new_content + '</sub>' + line[m.end():]
                n += 1
                fixed = True
                break
            else:
                # 多字母 → 正体；混合例外按映射
                if in_em:
                    line = split_em_around(line, m.start(), m.end())
                    n += 1
                    fixed = True
                    break
                if core in MIXED_MAP:
                    new_content = MIXED_MAP[core]
                    line = line[:m.start()] + '<sub>' + new_content + '</sub>' + line[m.end():]
                    n += 1
                    fixed = True
                    break
                m = SUB_RE.search(line, m.end())
                continue
        if not fixed:
            break
    return line, n


def in_em_at(line, pos):
    """pos 处是否处于 markdown *em* 或 <em>/<i> 标签内。跳过 sub/sup 内部与标签。"""
    em = 0
    i = 0
    open_tags = []
    while i < pos:
        c = line[i]
        if c == '<':
            m2 = TAG_RE.match(line, i)
            tag = m2.group(0)
            name = re.match(r'</?([a-zA-Z]+)', tag)
            if name:
                nm = name.group(1).lower()
                if nm in ('em', 'i'):
                    open_tags.append(nm) if not tag.startswith('</') else None
                    if tag.startswith('</') and open_tags:
                        open_tags.pop()
            i = m2.end()
            continue
        if c == '*':
            em ^= 1
        i += 1
    return bool(em) or bool(open_tags)


def split_em_around(line, start, end):
    """把覆盖 <sub> 的 markdown em 在 sub 边界处断开。"""
    i = end
    depth = 1
    while i < len(line):
        c = line[i]
        if c == '<':
            m2 = TAG_RE.match(line, i)
            i = m2.end()
            continue
        if c == '*':
            depth ^= 1
            if depth == 0:
                break
        i += 1
    closer = i
    if closer == end:  # 形如 *X<sub>abc</sub>*：closer 紧贴 </sub>
        line = line[:start] + '*' + line[start:closer] + line[closer + 1:]
    else:  # em 还在延续：闭在 sub 前、重开在 sub 后
        line = line[:start] + '*' + line[start:end] + '*' + line[end:]
    return line


def main():
    total_sub = total_math = 0
    for path in sorted(glob.glob('docs/ch0*.md')) + ['docs/index.md']:
        content = open(path, encoding='utf-8').read()
        # 1) 公式侧
        spans = []

        def stash(m):
            spans.append(m.group(0))
            return f'\x00{len(spans)-1}\x00'
        protected = MATH.sub(stash, content)
        # 2) 正文侧：先规范化 sub 内 *x* → <em>x</em>
        protected = re.sub(r'<sub>\*([A-Za-z])\*</sub>', r'<sub><em>\1</em></sub>', protected)
        nsub = 0
        lines = protected.split('\n')
        for idx, ln in enumerate(lines):
            ln2, k = sub_fix_line(ln)
            if k:
                lines[idx] = ln2
                nsub += k
        protected = '\n'.join(lines)
        # 3) 还原公式并修公式下标
        def unstash(m):
            idx = int(m.group(1))
            seg, k = math_fix(spans[idx])
            nonlocal_total[0] += k
            return seg
        nonlocal_total = [0]
        out = re.sub(r'\x00(\d+)\x00', unstash, protected)
        if out != content:
            with open(path, 'w', encoding='utf-8', newline='') as f:
                f.write(out)
        print(f'{path}: text-sub {nsub}, math-sub {nonlocal_total[0]}')
        total_sub += nsub
        total_math += nonlocal_total[0]
    print(f'TOTAL text={total_sub} math={total_math}')


if __name__ == '__main__':
    main()
