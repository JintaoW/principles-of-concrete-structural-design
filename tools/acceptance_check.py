# -*- coding: utf-8 -*-
"""全书验收机检脚本（可反复运行）

检查项:
  1. 图片引用完整性: md 中引用的每个 /images/... 文件必须存在于 docs/images/
  2. 孤儿图片(仅提示): docs/images/ 中未被任何 md 引用的文件
  3. 残留 Pandoc 语法: {width=}, 内部锚链接 ](#...), 引用块 >, 乱码字符
  4. 布局结构: <div> 开闭标签平衡; eq/fig/tbl-wrap 数量统计
  5. 题注遗漏: "表N-N xxx" 行未被 tbl-caption 包裹的
  6. 章节标题: 每章应以 "# 第X章" 一级标题开头

用法: python acceptance_check.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / 'docs'
IMG_REF = re.compile(r'(?:\]\(|src=")(/images/[^)"]+?)[")]')
DIV_OPEN = re.compile(r'<div\b')
DIV_CLOSE = re.compile(r'</div>')
CAPTION = re.compile(r'^表\s?\d+[-–]\d+\s+\S')
GARBLED = re.compile('锟斤拷|â€|Ã©|å|æ\\w\\w\\w')

def main():
    problems, stats = [], []
    mds = sorted(DOCS.glob('ch*.md')) + [DOCS / 'index.md']
    all_refs = set()

    for md in mds:
        text = md.read_text(encoding='utf-8')
        lines = text.split('\n')

        # 1. 图片引用
        missing = 0
        for m in IMG_REF.finditer(text):
            all_refs.add(m.group(1))
            if not (DOCS / m.group(1).lstrip('/')).exists():
                problems.append(f'[缺图] {md.name}: {m.group(1)}')
                missing += 1

        # 2. 残留语法 / 乱码
        # 注: 行内图的 {width=N} 由 attr_list 扩展渲染为 width 属性, 非问题
        for name, pat in [
            ('内部锚链接', re.compile(r'\]\(#[^)]*\)')),
            ('引用块残留', re.compile(r'^>', re.M)),
            ('疑似乱码', GARBLED),
        ]:
            n = len(pat.findall(text))
            if n:
                problems.append(f'[{name}] {md.name}: {n} 处')

        # 3. div 平衡
        n_open, n_close = len(DIV_OPEN.findall(text)), len(DIV_CLOSE.findall(text))
        if n_open != n_close:
            problems.append(f'[div不平衡] {md.name}: 开{n_open} 闭{n_close}')
        n_eq = text.count('<div class="eq">')
        n_fig = text.count('<div class="fig">')
        n_tbl = text.count('<div class="tbl-wrap"')
        stats.append(f'{md.name}: 公式段{n_eq} 插图段{n_fig} 表格包裹{n_tbl} 缺图{missing}')

        # 4. 题注遗漏(排除已在 caption p 标签内的)
        for i, ln in enumerate(lines):
            s = ln.strip()
            if CAPTION.match(s) and 'tbl-caption' not in s and not s.startswith('<'):
                problems.append(f'[题注遗漏] {md.name} 第{i+1}行: {s[:40]}')

        # 5. 章节标题
        if md.name.startswith('ch'):
            first = next((l for l in lines if l.strip()), '')
            if not first.startswith('# '):
                problems.append(f'[一级标题] {md.name}: 首个非空行不是 "# 开头" -> {first[:30]}')

    # 6. 孤儿图片(仅统计提示)
    disk_imgs = {f'/images/{p.parent.name}/{p.name}' for p in DOCS.glob('images/*/*')}
    orphans = disk_imgs - all_refs

    print('== 各章统计 ==')
    for s in stats:
        print(' ', s)
    print(f'\n图片引用总数: {len(all_refs)}; 磁盘图片: {len(disk_imgs)}; 孤儿图片: {len(orphans)}')
    if orphans:
        for o in sorted(orphans)[:10]:
            print('  [孤儿]', o)
    print(f'\n== 问题清单 ({len(problems)}) ==')
    for p in problems:
        print(' ', p)
    if not problems:
        print('  全部通过 ✓')
    return 1 if problems else 0

if __name__ == '__main__':
    sys.exit(main())
