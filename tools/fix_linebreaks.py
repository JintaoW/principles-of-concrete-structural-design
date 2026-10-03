# -*- coding: utf-8 -*-
r"""把公式内的失效断行 \\ 与 \,\, 分隔符改写为 MathJax 真正支持的
\begin{aligned} 环境，并在关系符处加 & 对齐（教材排法）。
只处理含 \displaystyle 的行内公式 span；行内 $...$ 短式不动。
幂等：已含 \begin{aligned} 的行跳过。
"""
import re, glob

REL = ('=', '<', '>')

def split_segments(content):
    # 按 \\ 或 \,\, 切分（文件中字面双反斜杠）
    parts = re.split(r'\\\\|\\,\\,', content)
    segs = []
    for p in parts:
        p = p.strip()
        if p.startswith('\\,'):  # 只剥离完整的 \, 分隔符，不碰其他反斜杠
            p = p[2:].strip()
        if p:
            segs.append(p)
    return segs

def align_segment(seg, is_first):
    if is_first:
        # 在第一个顶层 = 前插入 &（第一个 = 必为主关系符）
        i = seg.find('=')
        if i > 0:
            return seg[:i] + '&' + seg[i:]
        return seg
    if seg.startswith(REL):
        return '&' + seg
    # 以标识符开头且紧跟 =（如 N_e=...）：在 = 前插 &
    m = re.match(r'^([^=]{1,45}?)=', seg)
    if m and '(' not in m.group(1) and '\\' not in m.group(1):
        return seg[:m.end(1)] + '&' + seg[m.end(1):]
    return '&\\quad ' + seg

def transform_line(line):
    if '\\begin{aligned}' in line or '\\displaystyle' not in line:
        return line
    m = re.search(r'\\\( \\displaystyle (.*?) \\\)', line)
    if not m or '\\\\' not in m.group(1):
        return line
    segs = split_segments(m.group(1))
    if len(segs) < 2:
        return line
    aligned = '\\begin{aligned} ' + ' \\\\ '.join(
        align_segment(s, i == 0) for i, s in enumerate(segs)) + ' \\end{aligned}'
    return line[:m.start()] + '\\( \\displaystyle ' + aligned + ' \\)' + line[m.end():]

count = 0
for path in sorted(glob.glob('docs/ch0*.md')):
    lines = open(path, encoding='utf-8').read().split('\n')
    changed = 0
    for i, line in enumerate(lines):
        new = transform_line(line)
        if new != line:
            lines[i] = new
            changed += 1
    if changed:
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write('\n'.join(lines))
        print(f'{path}: {changed} lines -> aligned')
        count += changed
print('TOTAL:', count)
