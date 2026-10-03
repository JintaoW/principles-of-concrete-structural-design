# -*- coding: utf-8 -*-
"""MathType(DSMT4) 公式 LaTeX 提取主控(64位Python)。

流程: 对每章 docx 副本, 按文档顺序找出 DSMT4 OLE 及其媒体映射 -> 从嵌入
oleObjectN.bin 的 "Equation Native" 流剥掉28字节头得到 MTEF -> 调 32 位
Python + MathPage.WLL 的 MathType SDK 把 MTEF 批量翻译为 LaTeX -> 写
work/extract/<chNN>_mt_latex.json（与 extract_latex.py 的 json 同构）。
用法: python mt_translate.py <chNN> [<chNN>...]
"""
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTRACT = ROOT / 'work' / 'extract'
# MathPage.wll 64位可直接由64位Python加载; 若换32位WLL需换用 work/py32/python.exe
PYWORKER = Path(r'C:/Users/Jintao Wang/.workbuddy/binaries/python/envs/default/Scripts/python.exe')
HERE = Path(__file__).resolve().parent


def dsmt_list(docx_path: Path):
    """按文档顺序返回 [(ole_idx, media, mtef_bytes)]。"""
    import io
    import olefile
    with zipfile.ZipFile(docx_path) as z:
        doc = z.read('word/document.xml').decode('utf-8')
        rels = z.read('word/_rels/document.xml.rels').decode('utf-8')
        rid = {m.group(1): m.group(2) for m in
               re.finditer(r'Id="(rId\d+)"[^>]*Target="([^"]+)"', rels)}
        bins = {}
        for m in re.finditer(r'<w:object\b.*?</w:object>', doc, re.S):
            blk = m.group(0)
            pid = re.search(r'ProgID="([^"]+)"', blk)
            if not (pid and 'DSMT' in pid.group(1)):
                continue
            r = re.search(r'<o:OLEObject[^>]*r:id="([^"]+)"', blk).group(1)
            bins[r] = z.read('word/' + rid[r])
    out = []
    for i, m in enumerate(re.finditer(r'<w:object\b.*?</w:object>', doc, re.S), 1):
        blk = m.group(0)
        pid = re.search(r'ProgID="([^"]+)"', blk)
        if not (pid and 'DSMT' in pid.group(1)):
            continue
        r = re.search(r'<o:OLEObject[^>]*r:id="([^"]+)"', blk).group(1)
        media = ''
        img = re.search(r'<v:imagedata[^>]*r:id="([^"]+)"', blk)
        if img:
            media = rid.get(img.group(1), '').split('/')[-1]
        ole = olefile.OleFileIO(io.BytesIO(bins[r]))
        eq = ole.openstream('Equation Native').read()[28:]  # 剥 EQNOLEFILEHDR
        out.append((i, media, eq))
    return out


def main(chapters):
    for ch in chapters:
        docx = EXTRACT / f'{ch}.docx'
        items = dsmt_list(docx)
        print(f'{ch}: DSMT4 {len(items)} 个')
        if not items:
            (EXTRACT / f'{ch}_mt_latex.json').write_text(
                json.dumps({'chapter': ch, 'oles': []}, ensure_ascii=False),
                encoding='utf-8')
            continue
        mdir = EXTRACT / f'{ch}_mtef'
        mdir.mkdir(exist_ok=True)
        for j, (_, _, eq) in enumerate(items, 1):
            (mdir / f'{j:04d}.bin').write_bytes(eq)
        r = subprocess.run([str(PYWORKER), str(HERE / 'mt_translate32.py'), str(mdir)],
                           capture_output=True, text=True, timeout=600)
        print(r.stdout.strip())
        if r.returncode != 0:
            print(r.stderr[-500:])
            print(f'!! {ch} 翻译子进程失败, 中止')
            continue
        results = []
        for j, (idx, media, _) in enumerate(items, 1):
            txt = (mdir / f'{j:04d}.txt').read_text(encoding='utf-8')
            latex = None if txt.startswith('__FAIL__') else txt  # MathJax-LaTeX 翻译器自带 \\(...\\) 定界
            results.append([idx, 'Equation.DSMT4', media, latex])
        out = EXTRACT / f'{ch}_mt_latex.json'
        out.write_text(json.dumps({'chapter': ch, 'oles': results},
                                  ensure_ascii=False, indent=1), encoding='utf-8')
        n_ok = sum(1 for r in results if r[3])
        print(f'{ch}: 已写入 {out.name} (成功{n_ok}/{len(items)})')
        for r in results[:2]:
            if r[3]:
                print('  样例:', r[3][:110])


if __name__ == '__main__':
    main(sys.argv[1:] or ['ch02'])
