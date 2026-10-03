# -*- coding: utf-8 -*-
r"""下标正斜体铁律最终清理（第二轮扩展）：
1) 裸/花括号单字母 TARGETS 扩展至 a,d,h,k,l,m,n,p,q,u,v（全部说明性缩写）
2) 复合形态精确替换：σ_lN、ψ_f1、a_f,max/lim、ψ_q1、σ_s1、ψ_{c_j}、S_{A_d}、
   S_{G_jk}、S_{Q_1k}、e_{0b,min}、N_{ux/uy/u0}、σ_{p0}、ρ_{sv,min}、α_{s,max}、
   S_{d,dst/stb}、\boldsymbol{pe/con}
保持斜体：序号 i/j、轴号 x/y、作用量符号 G/Q/L/A 基、\min/\max/\lim 宏（自动正体）
"""
import glob, re

# 数学：裸单字母（后跟字母=连写新基，同样转换）
MATH_TARGETS = 'adhklmnpquv'
# 正文：外层em/内层em 斜体下标（i/j/x/y 除外）
TEXT_TARGETS = 'adhklmnpquv'

COMPOUND = [
    (r'_\{l([1-9])\}', r'_{\\mathrm{l}\1}'),          # σ_l1..l6
    (r'_\{f1\}', r'_{\\mathrm{f}1}'),                 # ψ_f1 频遇
    (r'_\{f,\\max\}', r'_{\\mathrm{f},\\max}'),       # a_f,max
    (r'_\{f,\\lim\}', r'_{\\mathrm{f},\\lim}'),       # a_f,lim
    (r'_\{q1\}', r'_{\\mathrm{q}1}'),                 # ψ_q1
    (r'_\{s1\}', r'_{\\mathrm{s}1}'),                 # σ_s1
    (r'_\{c_j\}', r'_{\\mathrm{c}_j}'),               # ψ_cj (c正体,j斜体)
    (r'_\{A_d\}', r'_{A_{\\mathrm{d}}}'),             # S_{A_d} (A作用量斜体)
    (r'_\{G_jk\}', r'_{G_{j\\mathrm{k}}}'),           # S_Gjk (j斜k正)
    (r'_\{Q_1k\}', r'_{Q_{1\\mathrm{k}}}'),           # S_Q1k
    (r'_\{Q_\{1k\}\}', r'_{Q_{1\\mathrm{k}}}'),
    (r'_\{ux\}', r'_{\\mathrm{u}x}'),                 # N_ux (u正x斜)
    (r'_\{uy\}', r'_{\\mathrm{u}y}'),
    (r'_\{u0\}', r'_{\\mathrm{u}0}'),
    (r'_\{p0\}', r'_{\\mathrm{p}0}'),                 # σ_p0
    (r'_\{sv,\\min\}', r'_{\\mathrm{sv},\\min}'),
    (r'_\{s,\\max\}', r'_{\\mathrm{s},\\max}'),
    (r'_\{d,dst\}', r'_{\\mathrm{d},\\mathrm{dst}}'),
    (r'_\{d,stb\}', r'_{\\mathrm{d},\\mathrm{stb}}'),
    (r'_\{0b,\\min\}', r'_{0\\mathrm{b},\\min}'),     # e_0b,min
    (r'_\{\\boldsymbol\{pe\}\}', r'_{\\mathrm{pe}}'),
    (r'_\{\\boldsymbol\{con\}\}', r'_{\\mathrm{con}}'),
]

total = 0
for path in sorted(glob.glob('docs/ch0*.md')) + ['docs/index.md']:
    content = open(path, encoding='utf-8').read()
    n0 = total
    # 复合形态（先做，避免被单字母规则抢先吃掉字母）
    for pat, rep in COMPOUND:
        content, k = re.subn(pat, rep, content)
        total += k
    # 花括号单字母
    content, k = re.subn(r'_\{([' + MATH_TARGETS + r'])\}', lambda m: '_{\\mathrm{' + m.group(1) + '}}', content)
    total += k
    # 裸字母
    content, k = re.subn(r'_([' + MATH_TARGETS + r'])(?!\{)', lambda m: '_{\\mathrm{' + m.group(1) + '}}', content)
    total += k
    # 正文：内层 em
    content, k = re.subn(r'<sub><em>([' + TEXT_TARGETS + r'])</em></sub>', r'<sub>\1</sub>', content)
    total += k
    # 正文：外层 em（基符号可为 σ 等非ASCII；容忍下标尾空格）
    content, k = re.subn(r'\*([^*<]+?)<sub>([' + TEXT_TARGETS + r']) ?</sub>\*',
                         r'*\1*<sub>\2</sub>', content)
    total += k
    if total > n0:
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write(content)
print('TOTAL changed:', total)
