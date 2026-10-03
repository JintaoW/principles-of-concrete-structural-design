# -*- coding: utf-8 -*-
"""阶段1: 盘点 docs/ch*.md 中全部 HTML 符号形态, 分类统计, 供白名单转换规则制定。"""
import re, glob, collections

pat = re.compile(
    r'\*(?P<base>[^*\n]+?)\*'                       # *base* 斜体基符
    r'(?P<scripts>(?:<su[bp]>[^<]*</su[bp]>)+)?'    # 跟随的上下标(可多个)
)

def classify(base):
    if re.fullmatch(r'[A-Za-z]', base): return '拉丁单字母'
    if re.fullmatch(r'[A-Za-z]{2,}', base): return '拉丁多字母(需人工)'
    if all(('\u0370' <= c <= '\u03ff') or ('\u1f00' <= c <= '\u1fff') for c in base):
        return '希腊字母'
    return '其他(需人工)'

def classify_sub(s):
    s2 = re.sub(r'<[^>]+>', '', s)
    if re.fullmatch(r'[0-9]+', s2): return '纯数字'
    if re.fullmatch(r"[A-Za-z']+", s2): return '拉丁字母/撇号'
    if all(('\u0370' <= c <= '\u03ff') for c in s2 if not c in ', '): return '希腊'
    return '混合(需人工)'

stats = collections.Counter()
examples = collections.defaultdict(list)
total = 0
for path in sorted(glob.glob('docs/ch*.md')):
    text = open(path, encoding='utf-8').read()
    for m in pat.finditer(text):
        total += 1
        b, sc = classify(m.group('base')), m.group('scripts') or ''
        # 下标形态
        subs = re.findall(r'<sub>([^<]*(?:<em>[^<]*</em>)?[^<]*)</sub>', sc)
        sups = re.findall(r'<sup>([^<]*(?:<em>[^<]*</em>)?[^<]*)</sup>', sc)
        combo = f"基:{b}"
        if subs: combo += f" 下标:{classify_sub('|'.join(subs))}×{len(subs)}"
        if sups: combo += f" 上标:{classify_sub('|'.join(sups))}×{len(sups)}"
        if '<em>' in sc: combo += " 含嵌套em"
        stats[combo] += 1
        if stats[combo] <= 3 or '人工' in combo:
            examples[combo].append(f"{path}:{text[:m.start()].count(chr(10))+1}: {m.group(0)[:50]}")

print(f'总符号单元数: {total}\n')
for k, v in stats.most_common():
    print(f'{v:5d}  {k}')
print()
print('== 需人工确认形态的样例 ==')
for k, v in sorted(examples.items()):
    if '人工' in k:
        for e in v[:12]: print(' ', e)
print()
print('== 各形态首例 ==')
for k, v in sorted(examples.items()):
    if '人工' not in k:
        print(f'[{k}]'); print(' ', v[0])
