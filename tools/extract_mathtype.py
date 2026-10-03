# -*- coding: utf-8 -*-
"""MathType(DSMT4) OLE 公式 LaTeX 提取器。

原理: 加载 MathType 的 Word 模板(MathType Commands 2016.dotm)为临时加载项,
调用其公开宏 DoConvertEquations 在【副本】上批量把 MathType 公式原地转换为
TeX 文本(翻译器 MathJax-LaTeX.tdl), 再按文档顺序解析文本公式, 与转换前记录的
DSMT4 OLE 媒体映射逐一配对。

用法: python extract_mathtype.py <chNN>
输出: work/extract/<chNN>_mt_latex.json
"""
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

import pythoncom
import win32com.client

ROOT = Path(__file__).resolve().parent.parent
EXTRACT = ROOT / 'work' / 'extract'
MT_TPL32 = Path(r'D:\Program Files (x86)\MathType\Office Support\32\MathType Commands 2016.dotm')
MT_TPL64 = Path(r'D:\Program Files (x86)\MathType\Office Support\64\MathType Commands 2016.dotm')
TRANSLATOR = 'MathJax-LaTeX.tdl'


def dsmt_media_map(docx_path: Path):
    """按文档顺序返回 DSMT4 OLE 的 [(ole_idx, media)]。"""
    import zipfile
    from xml.etree import ElementTree as ET
    with zipfile.ZipFile(docx_path) as z:
        doc = z.read('word/document.xml').decode('utf-8')
        rels = z.read('word/_rels/document.xml.rels').decode('utf-8')
    rid_target = {rel.get('Id'): rel.get('Target') for rel in ET.fromstring(rels)}
    out = []
    for i, m in enumerate(re.finditer(r'<w:object\b.*?</w:object>', doc, re.S), 1):
        blk = m.group(0)
        pid_m = re.search(r'ProgID="([^"]+)"', blk)
        if not pid_m or 'DSMT' not in pid_m.group(1):
            continue
        img_m = re.search(r'<v:imagedata[^>]*r:id="([^"]+)"', blk)
        media = ''
        if img_m:
            media = rid_target.get(img_m.group(1), '').split('/')[-1]
        out.append((i, media))
    return out


def converted_tex_list(docx_path: Path):
    """转换后的 docx: 按文档顺序提取 \\(...\\) 文本公式。"""
    with zipfile.ZipFile(docx_path) as z:
        doc = z.read('word/document.xml').decode('utf-8')
    # 逐段落取文本, 再在段内找 \( ... \) (w:t 拆分已按段落合并)
    texs = []
    for pm in re.finditer(r'<w:p\b.*?</w:p>', doc, re.S):
        ptxt = ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', pm.group(0)))
        for m in re.finditer(r'\\\((.+?)\\\)', ptxt):
            texs.append(m.group(1))
    return texs


def main(ch: str):
    src = EXTRACT / f'{ch}.docx'
    work = EXTRACT / f'{ch}_mt.docx'
    shutil.copyfile(src, work)

    pre_map = dsmt_media_map(src)
    print(f'{ch}: DSMT4 OLE {len(pre_map)} 个')

    tpl = MT_TPL64 if MT_TPL64.exists() else MT_TPL32
    pythoncom.CoInitialize()
    word = win32com.client.gencache.EnsureDispatch('Word.Application')
    word.Visible = False
    word.DisplayAlerts = 0
    try:
        # 检测 Word 位数选择模板目录
        try:
            winword = str(word.Path)
            tpl = MT_TPL32 if '(x86)' in winword else MT_TPL64
        except Exception:
            pass
        assert tpl.exists(), tpl
        addin = word.AddIns.Add(str(tpl), False)  # 不写入 STARTUP, 仅本次会话
        addin.Installed = True

        word.Documents.Open(str(work), ReadOnly=False)
        doc = word.ActiveDocument
        cnt = 0
        word.Run('DoConvertEquations', False, 1, False, False, TRANSLATOR, 0, cnt)
        doc.Save()
        doc.Close(False)
        word.AddIns.Unload = True  # noop safeguard
    finally:
        try:
            for a in word.AddIns:
                if 'MathType' in a.Name:
                    a.Delete()
        except Exception:
            pass
        word.Quit()

    texs = converted_tex_list(work)
    print(f'转换后文本公式: {len(texs)} 个 (预期 {len(pre_map)})')
    if len(texs) != len(pre_map):
        print('!! 数量不匹配, 中止写结果')
        return
    results = [[idx, 'Equation.DSMT4', media, '\\(' + t + '\\)']
               for (idx, media), t in zip(pre_map, texs)]
    out = EXTRACT / f'{ch}_mt_latex.json'
    out.write_text(json.dumps({'chapter': ch, 'oles': results},
                              ensure_ascii=False, indent=1), encoding='utf-8')
    print('已写入', out)
    for t in texs[:3]:
        print('  样例:', t[:100])


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'ch02')
