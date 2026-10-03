# -*- coding: utf-8 -*-
"""
阶段B: 将"标签: $公式$ (编号)"形态的伪展示公式行升级为 .eq 独立公式块
阶段A: 将正文段落内行内公式的 \\frac 分式改为单排斜杠形式
均幂等。只处理 docs/ch*.md；不动 class="eq-body" 行(独立公式保持堆叠分式)。
"""
import re, glob, sys

# ---------------- 阶段B: 伪展示公式行 -> .eq 块 ----------------
PSEUDO = re.compile(r'^(.*?)\$([^$]+)\$\s*\((\d+-[0-9a-z,]+)\)\s*$')

def promote_pseudo(lines):
    out, n = [], 0
    for line in lines:
        m = PSEUDO.match(line.rstrip('\n'))
        if m and 'eq-body' not in line and '$' in line:
            label, math, no = m.group(1).strip(), m.group(2).strip(), m.group(3)
            out.append(f'{label}\n\n')
            out.append('<div class="eq">\n')
            out.append(f'  <span class="eq-body"><span class="arithmatex">\\( \\displaystyle {math} \\)</span></span>'
                       f'<span class="eq-no">({no})</span>\n')
            out.append('</div>\n')
            n += 1
            print(f'  [B] 升级: {label[:30]} ... ({no})')
        else:
            out.append(line)
    return out, n

# ---------------- 阶段A: 行内 \frac -> 单排 ----------------
def find_group(s, i):
    """s[i]=='{', 返回 (内容, 结束后位置)"""
    depth = 0
    for j in range(i, len(s)):
        if s[j] == '{': depth += 1
        elif s[j] == '}':
            depth -= 1
            if depth == 0: return s[i+1:j], j+1
    return None, -1

def strip_outer_braces(g):
    while g.startswith('{') and g.endswith('}'):
        _, end = find_group(g, 0)
        if end == len(g):
            g = g[1:-1].strip()
        else:
            break
    return g

OPS = set('+-=/')

def has_top_ops(g):
    """深度0处是否有 + - = / 或 \\times 等二元运算命令"""
    depth = 0; i = 0
    while i < len(g):
        c = g[i]
        if c == '{': depth += 1
        elif c == '}': depth -= 1
        elif depth == 0:
            if c in OPS: return True
            if c == '\\':
                m = re.match(r'\\([a-zA-Z]+)', g[i:])
                if m:
                    if m.group(1) in ('times','cdot','pm','mp','div','cup','cap'):
                        return True
                    i += len(m.group(0)); continue
        i += 1
    return False

def count_atoms(g):
    """深度0原子数: \\cmd{arg}/\\cmd(含上下标) | {..} | 字母串 | 数字串"""
    g = g.strip(); depth = 0; atoms = 0; i = 0; n = len(g)
    while i < n:
        c = g[i]
        if c == '{':
            if depth == 0:
                _, end = find_group(g, i); i = end
                atoms += 1
                continue
            depth += 1
        elif c == '}':
            depth -= 1
        elif depth == 0 and c not in ' \t':
            if c == '\\':
                m = re.match(r'\\[a-zA-Z]+', g[i:])
                if not m: i += 1; continue
                i += len(m.group(0))
                j = i
                while j < n and g[j] in ' \t': j += 1
                if j < n and g[j] == '{':
                    _, end = find_group(g, j); i = end
            elif c in '()':
                i += 1
            else:
                m = re.match(r'[a-zA-Z]+|[0-9.]+', g[i:])
                if not m: i += 1; continue
                i += len(m.group(0))
            # 跳过可选空格后吃掉后续上下标
            while True:
                j = i
                while j < n and g[j] in ' \t': j += 1
                if j < n and g[j] in '^_' and (j == i or j - i <= 4):
                    i = j + 1
                    if i < n and g[i] == '{':
                        _, end = find_group(g, i); i = end
                    elif i < n:
                        m = re.match(r'\\[a-zA-Z]+|[a-zA-Z0-9]', g[i:])
                        if m: i += len(m.group(0))
                        else: i += 1
                else:
                    break
            atoms += 1
            continue
        i += 1
    return atoms

def frac_to_slash(s):
    """最内层优先, 反复直到无 \\frac"""
    changed = True
    while changed:
        changed = False
        i = 0
        while True:
            k = s.find('\\frac{', i)
            if k < 0: break
            x, j = find_group(s, k + 5)
            if x is None: i = k + 1; continue
            # 跳过空白
            m = re.match(r'\s*', s[j:]); j2 = j + m.end()
            if j2 >= len(s) or s[j2] != '{': i = k + 1; continue
            y, j3 = find_group(s, j2)
            if y is None: i = k + 1; continue
            if '\\frac' in x or '\\frac' in y:   # 先处理内层
                i = k + 1; continue
            xs, ys = strip_outer_braces(x.strip()), strip_outer_braces(y.strip())
            xs_s = xs if (_pre_parenthesized(xs) or not has_top_ops(xs)) \
                   else r'\left( ' + xs + r' \right)'
            y_paren = ys if _pre_parenthesized(ys) else None
            if y_paren is None:
                ys_bare = (not has_top_ops(ys)) and count_atoms(ys) <= 1
            else:
                ys_bare = False
            ys_s = ys if ys_bare else r'\left( ' + ys + r' \right)'
            # 紧跟乘数时, 裸单原子分母须加括号, 防止后续因子被读入分母;
            # 但后续因子是 \left(..\right) 时除外(左结合下值不变且形态自然)
            m2 = re.match(r'\s*(?!\\left\()[a-zA-Z0-9\\{]', s[j3:])
            if ys_bare and m2:
                ys_s = r'\left( ' + ys + r' \right)'
            # 花括号噪声清理: 非上下标的纯分组括号剥离(跳过\command的参数)
            xs_s = _strip_group_noise(xs_s)
            ys_s = _strip_group_noise(ys_s)
            # 原子级单原子判定: \left(..\right) 整体算单原子
            s = s[:k] + xs_s + '/' + ys_s + s[j3:]
            changed = True
            i = k + len(xs_s) + 1 + len(ys_s)
        # end while True
    return s

def _pre_parenthesized(g):
    return g.startswith(r'\left(') and g.endswith(r'\right)')

def _strip_group_noise(s):
    """剥离纯分组花括号: 字母/数字/)/} 后跟 {内容}, 且花括号前的字母串
    不是 \\command 的一部分; _{..}/^{..} 上下标不动"""
    out = []; i = 0; n = len(s)
    while i < n:
        c = s[i]
        if c == '{' and i > 0:
            # 回溯: 前面是否 _ ^ 或 \command
            j = i - 1
            if j >= 0 and s[j] in '_^':
                out.append(c); i += 1; continue
            k = j
            while k >= 0 and s[k].isalpha(): k -= 1
            if k >= 0 and s[k] == '\\':
                out.append(c); i += 1; continue
            _, end = find_group(s, i)
            if end is not None:
                inner = s[i+1:end-1]
                if inner and not re.search(r'[{}]', inner):
                    out.append(inner); i = end; continue
        out.append(c); i += 1
    return ''.join(out)

def process_inline_spans(line):
    """仅处理正文行内的 $...$ 与 \\(...\\) 片段
    排除: eq-body 行(独立公式)、表格单元格行(<td, 单元格公式保持堆叠)、
    含 \\displaystyle 的片段(显示式公式不压缩, 无需单排)"""
    if 'eq-body' in line or '<td' in line: return line, 0
    cnt = 0
    def repl(m):
        nonlocal cnt
        inner = m.group(1)
        if '\\frac' not in inner or '\\displaystyle' in inner: return m.group(0)
        new = frac_to_slash(inner)
        if new != inner:
            cnt += 1
        return '$' + new + '$'
    line = re.sub(r'\$([^$]+)\$', repl, line)
    def repl2(m):
        nonlocal cnt
        inner = m.group(1)
        if '\\frac' not in inner or '\\displaystyle' in inner: return m.group(0)
        new = frac_to_slash(inner)
        if new != inner: cnt += 1
        return '\\(' + new + '\\)'
    line = re.sub(r'\\\((.+?)\\\)', repl2, line)
    return line, cnt

# ---------------- 主流程 ----------------
phase = sys.argv[1] if len(sys.argv) > 1 else 'BA'   # B=仅升级, A=仅分式, BA=两阶段
for path in sorted(glob.glob('docs/ch*.md')):
    with open(path, encoding='utf-8') as f:
        lines = f.readlines()
    nb = na = 0
    if 'B' in phase:
        lines, nb = promote_pseudo(lines)
    if 'A' in phase:
        for idx, line in enumerate(lines):
            lines[idx], c = process_inline_spans(line)
            na += c
            if c: print(f'  [A] {path}:{idx+1} 行内分式改单排')
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.writelines(lines)
    print(f'{path}: 阶段B升级 {nb} 行, 阶段A转换 {na} 处')
