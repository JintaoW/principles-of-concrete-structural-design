# -*- coding: utf-8 -*-
"""AxMath OLE 公式 LaTeX 提取器（只读，不修改文档）。

用法: python extract_latex.py <chNN>
对 docx 副本( work/extract/<chNN>.docx )中每个 Equation.AxMath OLE：
  DoVerb(10)（无窗口模式）→ AxMath 把 LaTeX 放入剪贴板 → 读走。
同时解析 document.xml 建立 OLE文档顺序 → WMF媒体文件 的映射，
并与 docs/images/<chNN>/ 及 docs/<chNN>.md 的引用做对账。

输出: work/extract/<chNN>_latex.json
"""
import json
import re
import sys
import time
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pythoncom
import win32clipboard
import win32com.client
import winreg

ROOT = Path(__file__).resolve().parent.parent
EXTRACT = ROOT / 'work' / 'extract'
REG = r'Software\AxMath\WordCmds'

W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
V_NS = 'urn:schemas-microsoft-com:vml'
O_NS = 'urn:schemas-microsoft-com:office:office'
R_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
REL_NS = 'http://schemas.openxmlformats.org/package/2006/relationships'


def setflag(name: str, val: str):
    k = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG)
    winreg.SetValueEx(k, name, 0, winreg.REG_SZ, val)
    winreg.CloseKey(k)


def getflag(name: str):
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG)
        v, _ = winreg.QueryValueEx(k, name)
        winreg.CloseKey(k)
        return v
    except OSError:
        return None


def read_clip_text():
    for attempt in range(10):  # 剪贴板可能被其他进程短暂占用, 重试
        try:
            win32clipboard.OpenClipboard()
        except Exception:
            time.sleep(0.15)
            continue
        try:
            for fmt in (13, 1):  # CF_UNICODETEXT, CF_TEXT
                if win32clipboard.IsClipboardFormatAvailable(fmt):
                    d = win32clipboard.GetClipboardData(fmt)
                    return d if isinstance(d, str) else d.decode('utf-8', 'replace')
            return None
        finally:
            win32clipboard.CloseClipboard()
    return None


def ole_media_map(docx_path: Path):
    """按文档顺序返回 [(idx, progid, media_basename)]。"""
    with zipfile.ZipFile(docx_path) as z:
        doc = z.read('word/document.xml').decode('utf-8')
        rels = z.read('word/_rels/document.xml.rels').decode('utf-8')
    rid_target = {}
    for rel in ET.fromstring(rels):
        rid_target[rel.get('Id')] = rel.get('Target')
    out = []
    om = re.finditer(r'<w:object\b.*?</w:object>', doc, re.S)
    for i, m in enumerate(om, 1):
        blk = m.group(0)
        pid_m = re.search(r'ProgID="([^"]+)"', blk)
        img_m = re.search(r'<v:imagedata[^>]*r:id="([^"]+)"', blk)
        progid = pid_m.group(1) if pid_m else '(none)'
        media = ''
        if img_m:
            t = rid_target.get(img_m.group(1), '')
            media = t.split('/')[-1]
        out.append((i, progid, media))
    return out


def main(ch: str):
    docx = EXTRACT / f'{ch}.docx'
    assert docx.exists(), docx
    oles = ole_media_map(docx)
    print(f'{ch}: document.xml 中 OLE 对象 {len(oles)} 个')
    stats = {}
    for _, pid, _m in oles:
        stats[pid] = stats.get(pid, 0) + 1
    print('ProgID 分布:', stats)

    setflag('DoNoWinVerb', '1')
    pythoncom.CoInitialize()
    word = win32com.client.gencache.EnsureDispatch('Word.Application')
    word.Visible = False
    word.DisplayAlerts = 0
    results = []  # (ole_idx, progid, media, latex)
    try:
        word.Documents.Open(str(docx), ReadOnly=False)
        doc = word.ActiveDocument
        n = doc.InlineShapes.Count
        print(f'Word InlineShapes: {n}')
        t_start = time.time()
        for i, (ole_idx, pid, media) in enumerate(oles, 1):
            if 'AxMath' not in pid:
                results.append([ole_idx, pid, media, None])
                continue
            sh = doc.InlineShapes(i)
            try:
                real_pid = sh.OLEFormat.ProgID
            except Exception:
                real_pid = pid
            if 'AxMath' not in (real_pid or ''):
                results.append([ole_idx, real_pid, media, None])
                print(f'  #{ole_idx}: ProgID 不匹配({real_pid}), 跳过')
                continue
            setflag('WaitingConvert', '0')
            t0 = time.time()
            sh.OLEFormat.DoVerb(10)
            while getflag('WaitingConvert') != '1' and time.time() - t0 < 10:
                time.sleep(0.05)
            time.sleep(0.05)
            latex = read_clip_text()
            results.append([ole_idx, real_pid, media, latex])
            if latex is None:
                print(f'  #{ole_idx} ({media}): 提取失败!')
        doc.Close(False)
    finally:
        word.Quit()

    ok = sum(1 for r in results if r[3])
    fail = [r for r in results if r[3] is None and 'AxMath' in (r[1] or '')]
    dt = time.time() - t_start
    print(f'AxMath 提取: 成功 {ok} / 失败 {len(fail)}, 耗时 {dt:.1f}s')
    for r in fail:
        print('  失败:', r[:3])

    out = EXTRACT / f'{ch}_latex.json'
    out.write_text(json.dumps({
        'chapter': ch,
        'oles': results,
    }, ensure_ascii=False, indent=1), encoding='utf-8')
    print('已写入', out)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'ch02')
