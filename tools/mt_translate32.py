# -*- coding: utf-8 -*-
"""MathType MTEF -> LaTeX 翻译(32位专用, 由 mt_translate.py 用32位Python调用)。

直接 ctypes 调 MathPage.WLL 的 MathType SDK API:
  MTInitAPI -> MTXFormReset -> MTXFormSetTranslator(MathJax-LaTeX)
  -> MTXFormEqn(LOCAL, MTEF, bytes, len, LOCAL, TEXT, buf, ...) -> LaTeX 文本
用法: python(32) mt_translate32.py <mtef_dir>   # 目录内每个 *.bin -> *.txt
"""
import ctypes
import struct
import sys
from pathlib import Path

WLL = r'D:\Program Files (x86)\MathType\MathPage\64\MathPage.wll'
TRANSLATOR = b'MathJax-LaTeX.tdl'

mtxfmLOCAL = -3
mtxfmMTEF = 4
mtxfmTEXT = 7


class RECT(ctypes.Structure):
    _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long),
                ('right', ctypes.c_long), ('bottom', ctypes.c_long)]


class DIMS(ctypes.Structure):
    _fields_ = [('baseline', ctypes.c_short), ('bounds', RECT)]


def main(mtef_dir: str):
    import os
    for d in [r'D:\Program Files (x86)\MathType\MathPage\64',
              r'D:\Program Files (x86)\MathType\System\64',
              r'D:\Program Files (x86)\MathType',
              r'D:\Program Files (x86)\MathType\System']:
        if os.path.isdir(d):
            os.add_dll_directory(d)
    os.environ['PATH'] = r'D:\Program Files (x86)\MathType\System\64;' + \
                         r'D:\Program Files (x86)\MathType;' + os.environ['PATH']
    dll = ctypes.WinDLL(WLL)
    dll.MTInitAPI.restype = ctypes.c_long
    dll.MTInitAPI.argtypes = [ctypes.c_short, ctypes.c_short]
    dll.MTXFormReset.restype = ctypes.c_long
    dll.MTXFormSetTranslator.restype = ctypes.c_long
    dll.MTXFormSetTranslator.argtypes = [ctypes.c_short, ctypes.c_char_p]
    dll.MTXFormEqn.restype = ctypes.c_long
    dll.MTXFormEqn.argtypes = [ctypes.c_short, ctypes.c_short, ctypes.c_char_p,
                               ctypes.c_long, ctypes.c_short, ctypes.c_short,
                               ctypes.c_char_p, ctypes.c_long, ctypes.c_char_p,
                               ctypes.POINTER(DIMS)]

    stat = dll.MTInitAPI(0, 10)
    print('MTInitAPI:', stat, '(非零可容忍, 仅负值/后续失败才中止)')
    stat = dll.MTXFormReset()
    print('MTXFormReset:', stat)
    stat = dll.MTXFormSetTranslator(0, TRANSLATOR)
    print('MTXFormSetTranslator:', stat)
    if stat != 0:
        dll.MTTermAPI()
        sys.exit(3)

    ok = fail = 0
    for f in sorted(Path(mtef_dir).glob('*.bin')):
        mtef = f.read_bytes()
        buf = ctypes.create_string_buffer(20000)
        dims = DIMS()
        stat = dll.MTXFormEqn(mtxfmLOCAL, mtxfmMTEF, mtef, len(mtef),
                              mtxfmLOCAL, mtxfmTEXT, buf, 20000,
                              b' ', ctypes.byref(dims))
        if stat < 0:
            print(f'  {f.name}: stat={stat}')
            fail += 1
            f.with_suffix('.txt').write_text(f'__FAIL__{stat}', encoding='utf-8')
            continue
        text = buf.value.decode('gbk', 'replace').strip().rstrip('\x00').strip()
        f.with_suffix('.txt').write_text(text, encoding='utf-8')
        ok += 1
    try:
        dll.MTTermAPI()
    except Exception:
        pass
    print(f'翻译完成: 成功 {ok} / 失败 {fail}')


if __name__ == '__main__':
    main(sys.argv[1])
