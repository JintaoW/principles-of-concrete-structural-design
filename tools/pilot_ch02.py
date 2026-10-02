# -*- coding: utf-8 -*-
"""公式/插图 WMF → PNG 转换管线（试点：第二章）

流程:
  1. LibreOffice 无界面将 docx 提取出的 WMF 批量转为 3 倍分辨率 PNG（整页画布）
  2. 从 docx 的 document.xml 提取每个公式对象在 Word 中的显示尺寸(pt)
  3. Pillow 自动裁掉白边，缩放到 显示尺寸×2（retina 资产）
  4. 重写 Markdown 图片引用: ![](media/imageN.wmf) -> ![](images/chNN/eqN.png){width=Wpx}
"""
import re, os, subprocess, sys, json, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent   # 项目根 = tools/ 的上级目录（搬移目录无需改代码）
WORK = ROOT / 'work'
# 机器相关：需按实际安装位置修改（本机: LibreOffice 26.2.6）
SOFFICE = r'D:/Program Files/LibreOffice/program/soffice.com'
CANVAS_W, CANVAS_H = 2304, 3072   # 3x of default 768x1024 (A4 @96dpi)
PT2PX = 96.0 / 72.0

def step1_convert(media_dir: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    wmfs = sorted(media_dir.glob('*.wmf'))
    todo = [w for w in wmfs if not (out_dir / (w.stem + '.png')).exists()]
    if not todo:
        print(f'[step1] {len(wmfs)} 个 PNG 已存在，跳过转换')
        return
    # soffice 不接受过多通配？逐批传参
    cmd = [SOFFICE, '--headless',
           '--convert-to',
           f'png:draw_png_Export:{{"PixelWidth":{{"type":"long","value":{CANVAS_W}}},"PixelHeight":{{"type":"long","value":{CANVAS_H}}}}}',
           '--outdir', str(out_dir)] + [str(w) for w in todo]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
    ok = len(list(out_dir.glob('*.png')))
    print(f'[step1] 转换完成: {ok}/{len(wmfs)} 个 PNG')
    if ok < len(wmfs):
        print(r.stdout[-500:], r.stderr[-500:])

def step2_sizes(docx: Path) -> dict:
    """media文件名 -> Word 显示尺寸 (pt)"""
    z = zipfile.ZipFile(docx)
    rels = z.read('word/_rels/document.xml.rels').decode('utf-8', 'ignore')
    rid2target = dict(re.findall(r'Id="(rId\d+)"[^>]*?Target="([^"]+)"', rels))
    docxml = z.read('word/document.xml').decode('utf-8', 'ignore')
    z.close()
    sizes = {}
    for m in re.finditer(r'<v:(?:shape|rect|roundrect)\b[^>]*?style="([^"]*)"[^>]*?>(?:(?!</v:(?:shape|rect|roundrect)>).)*?<v:imagedata[^>]*?r:id="(rId\d+)"', docxml, re.S):
        style, rid = m.group(1), m.group(2)
        w = re.search(r'width:([\d.]+)pt', style)
        h = re.search(r'height:([\d.]+)pt', style)
        target = rid2target.get(rid, '')
        base = os.path.basename(target)
        if w and h and base:
            sizes[base] = (float(w.group(1)), float(h.group(1)))
    return sizes

def step3_trim_resize(png_dir: Path, final_dir: Path, sizes: dict, fallback_w_pt=30.0):
    from PIL import Image, ImageChops
    final_dir.mkdir(parents=True, exist_ok=True)
    report = {'ok': 0, 'fallback': 0}
    for png in sorted(png_dir.glob('*.png')):
        img = Image.open(png).convert('RGB')
        bg = Image.new('RGB', img.size, (255, 255, 255))
        bbox = ImageChops.difference(img, bg).getbbox()
        if bbox:
            x0, y0, x1, y1 = bbox
            m = 8
            x0 = max(0, x0 - m); y0 = max(0, y0 - m)
            x1 = min(img.width, x1 + m); y1 = min(img.height, y1 + m)
            img = img.crop((x0, y0, x1, y1))
        fname = png.stem + '.wmf'
        if fname in sizes:
            w_pt, h_pt = sizes[fname]
            report['ok'] += 1
        else:
            w_pt = fallback_w_pt
            h_pt = w_pt * img.height / max(1, img.width)
            report['fallback'] += 1
        disp_w = round(w_pt * PT2PX)          # CSS 显示宽度(px)
        target_w = disp_w * 2                  # 2x retina 资产
        target_h = max(1, round(target_w * img.height / img.width))
        img = img.resize((target_w, target_h), Image.LANCZOS)
        img.save(final_dir / (png.stem + '.png'))
    print(f"[step3] 裁剪缩放完成: {report}")

def step4_rewrite(md_path: Path, out_path: Path, media_dir_name: str, rel_img: str, sizes: dict):
    md = md_path.read_text(encoding='utf-8')
    n = [0]
    def repl(m):
        fname = m.group(1)
        stem = fname.rsplit('.', 1)[0]
        w_pt = sizes.get(fname, (None, None))[0]
        wattr = f'{{width={round(w_pt * PT2PX)}}} ' if w_pt else ''
        n[0] += 1
        return f'![]({rel_img}/{stem}.png){wattr.strip()}'
    md = re.sub(r'!\[\]\(' + re.escape(media_dir_name) + r'/media/([^)]+\.wmf)\)', repl, md)
    out_path.write_text(md, encoding='utf-8')
    print(f'[step4] Markdown 重写完成: {n[0]} 处图片引用 -> {out_path.name}')

if __name__ == '__main__':
    media = WORK / 'ch02_media' / 'media'
    raw = WORK / 'ch02_raw3x'
    final = ROOT / 'docs' / 'images' / 'ch02'
    step1_convert(media, raw)
    sizes = step2_sizes(WORK / 'ch02.docx')
    (WORK / 'ch02_sizes.json').write_text(json.dumps(sizes, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'[step2] 提取到 {len(sizes)} 个对象的显示尺寸')
    try:
        import PIL  # noqa
        step3_trim_resize(raw, final, sizes)
        step4_rewrite(WORK / 'ch02_docx.md', ROOT / 'docs' / 'ch02.md', 'ch02_media', '/images/ch02', sizes)
    except ImportError:
        print('[提示] Pillow 未安装，仅完成 step1/step2；安装 Pillow 后重跑本脚本即可')
