# -*- coding: utf-8 -*-
"""
阶段2试点: 将 HTML 斜体符号(*X*<sub>s</sub> 等)转换为 MathJax 行内公式。
白名单闸门: em 内容必须纯拉丁/希腊字母(可带’撇号), 中文/标点强调不碰。
下标语义映射复用铁律: ijxyGQLAzZ 斜体, 其余说明性缩写+数字正体(\mathrm)。
用法: python convert_html_symbols.py ch03   (章号或all)
幂等。跳过 eq-body 行。
"""
import re, sys, glob

GREEK = {
    'α':'\\alpha','β':'\\beta','γ':'\\gamma','δ':'\\delta','ε':'\\varepsilon',
    'ζ':'\\zeta','η':'\\eta','θ':'\\theta','κ':'\\kappa','λ':'\\lambda',
    'μ':'\\mu','ν':'\\nu','π':'\\pi','ρ':'\\rho','σ':'\\sigma','τ':'\\tau',
    'φ':'\\varphi','ϕ':'\\phi','χ':'\\chi','ψ':'\\psi','ω':'\\omega','ξ':'\\xi',
    'Δ':'\\varDelta','Φ':'\\Phi','Γ':'\\Gamma','Θ':'\\Theta','Λ':'\\Lambda',
    'Π':'\\Pi','Σ':'\\Sigma','Ω':'\\Omega','Ψ':'\\Psi'
}
ITALIC_SUB = set('ijGQLAzZN')   # 下标保持斜体: 序号ij/作用量GQLA/统计z/功能Z/内力N; x,y默认正体(材料下标), 轴号个案另判

# 主正则: *基符[’](内部脚本)* (外部脚本)*  — 基符仅拉丁或希腊
GK = ''.join(GREEK.keys())
UNIT = re.compile(
    r'(?<!\*)\*'
    r'(?P<base>[A-Za-z]+|[' + GK + r'])(?P<bprime>’?) ?'
    r'(?P<ins>(?:<su[bp]>(?P<i0>[^<]*)</su[bp]>)*?)'
    r'\*'
    r'(?P<outs>(?:<su[bp]>[^<]*(?:<em>[^<]*</em>)?[^<]*</su[bp]>)*)'
    r'(?!\*)'
)
# 单位上标: N/mm<sup>2</sup>、mm<sup>4</sup> 等(非em包裹的物理单位)
UNIT_POW = re.compile(r'(?P<u>[A-Za-z]+(?:/[A-Za-z]+)*)<sup>(?P<n>[0-9]+)</sup>')

OPS = {'max': '\\max', 'min': '\\min'}

def _seg_tex(seg):
    """单个逗号分隔段: 整词判定优先, 混合大小写再按字符"""
    if seg == "'": return seg
    if re.fullmatch(r'[0-9.]+', seg): return seg
    if seg in OPS: return OPS[seg]
    if re.fullmatch(r'[a-z]+[0-9]*', seg) and len(seg) >= 2:
        return '\\mathrm{' + seg + '}'        # 全小写词: 整体正体
    # 混合/含大写/单字符: 按字符语义分组
    out, run, run_ital = [], '', None
    def flush():
        nonlocal run, run_ital
        if not run: return
        out.append(run if run_ital else '\\mathrm{' + run + '}')
        run, run_ital = '', None
    for ch in seg:
        ital = (ch in ITALIC_SUB) if ch.isalpha() else False
        if run_ital is None: run_ital = ital
        if ital != run_ital:
            flush(); run_ital = ital
        run += ch
    flush()
    return ''.join(out)

def map_sub(s):
    """下标/上标内容 -> TeX (剥掉内嵌<em>标签, 按语义映射正斜体)"""
    s = s.replace('<em>', '').replace('</em>', '').strip()
    if s == '': return ''
    s = s.replace('’', "'")
    return ','.join(_seg_tex(seg) for seg in s.split(','))

def base_tex(b):
    if b in GREEK: return GREEK[b]
    return b

def scripts_tex(raw):
    """将连续的 <sub>x</sub><sup>y</sup> 串转 TeX"""
    out = []
    for m in re.finditer(r'<(su[bp])>(.*?)</\1>', raw):
        kind, content = m.group(1), m.group(2)
        tex = map_sub(content)
        if tex == '': continue
        mark = '_' if kind == 'sub' else '^'
        if tex == "'":
            out.append(tex)          # 撇号直接附加, 不带^
        else:
            out.append(mark + '{' + tex + '}')
    return ''.join(out)

def convert_line(line):
    n = 0
    def repl(m):
        nonlocal n
        tex = base_tex(m.group('base'))
        if m.group('bprime'): tex += "'"
        tex += scripts_tex(m.group('ins') or '')
        tex += scripts_tex(m.group('outs') or '')
        n += 1
        return '$' + tex + '$'
    if 'eq-body' in line: return line, 0
    def repl_u(m):
        nonlocal n
        n += 1
        return '$\\mathrm{' + m.group('u') + '^{' + m.group('n') + '}}$'
    line = UNIT_POW.sub(repl_u, line)
    new = UNIT.sub(repl, line)
    return new, n

target = sys.argv[1] if len(sys.argv) > 1 else 'ch03'
paths = sorted(glob.glob(f'docs/{target}.md')) if target != 'all' else sorted(glob.glob('docs/ch*.md'))
for path in paths:
    lines = open(path, encoding='utf-8').read().splitlines(keepends=True)
    total = 0
    for i, line in enumerate(lines):
        new, n = convert_line(line)
        if n:
            lines[i] = new
            total += n
            if target != 'all':
                print(f'{path.split(chr(92))[-1]}:{i+1}  ×{n}')
    open(path, 'w', encoding='utf-8', newline='').writelines(lines)
    print(f'== {path}: 转换 {total} 处')

# 复核: 剩余sub/sup统计
print('\n== 剩余HTML下标(应仅剩白名单外形态) ==')
for path in paths:
    text = open(path, encoding='utf-8').read()
    left = re.findall(r'<su[bp]>[^<]*</su[bp]>', text)
    if left:
        print(path, len(left), sorted(set(left))[:10])
