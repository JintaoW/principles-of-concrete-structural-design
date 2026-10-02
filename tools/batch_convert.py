# -*- coding: utf-8 -*-
"""章节批量转换管线（任一章通用，泛化自 pilot_ch02.py）

前置: 已用 pandoc 生成 work/ch<中文数>_docx.md 与 work/ch<中文数>_media/media/
流程:
  1. LibreOffice 将 WMF/EMF 批量转 3x 分辨率 PNG（整页画布, 分块防命令行超长）
  2. 从 document.xml 提取显示尺寸: VML(v:shape, pt) + drawingML(wp:extent, EMU->pt)
  3. WMF/EMF 产物: 裁白边 -> 缩放到 显示宽度x2 (retina, 不超原生) -> docs/images/chNN/v<stem>.png
     源生 PNG 插图: 原样复制 -> docs/images/chNN/<stem>.png
  4. 重写 Markdown 引用:
     - md 形式  ![](chX_media/media/imageN.wmf)      -> ![](/images/chNN/vimageN.png){width=Wpx}
     - html 形式 <img src="..." style="width:Ain;.."> -> <img src="/images/chNN/..." style="width:Xpx">
  5. 输出 docs/chNN.md

用法: python batch_convert.py 三 四 五 六 七 八 九
"""
import re, os, subprocess, sys, json, shutil, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent   # 项目根 = tools/ 的上级目录（搬移目录无需改代码）
WORK = ROOT / 'work'
# 机器相关：需按实际安装位置修改（本机: LibreOffice 26.2.6）
SOFFICE = r'D:/Program Files/LibreOffice/program/soffice.com'
CANVAS_W, CANVAS_H = 2304, 3072
PT2PX = 96.0 / 72.0

CH = {
    '一': ('01', '第一章 混凝土结构材料的性能'),
    '二': ('02', '第二章 混凝土结构设计方法'),
    '三': ('03', '第三章 钢筋混凝土轴心受力构件正截面承载力计算'),
    '四': ('04', '第四章 钢筋混凝土受弯构件正截面承载力计算'),
    '五': ('05', '第五章 钢筋混凝土受弯构件斜截面承载力计算'),
    '六': ('06', '第六章 钢筋混凝土受扭构件承载力计算'),
    '七': ('07', '第七章 钢筋混凝土偏心受力构件承载力计算'),
    '八': ('08', '第八章 钢筋混凝土构件的裂缝、变形和耐久性'),
    '九': ('09', '第九章 预应力混凝土构件设计'),
}

def step1_convert(media_dir: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    vecs = sorted(list(media_dir.glob('*.wmf')) + list(media_dir.glob('*.emf')))
    todo = [v for v in vecs if not (out_dir / (v.stem + '.png')).exists()]
    if not todo:
        print(f'[step1] {len(vecs)} 个矢量图 PNG 已存在，跳过')
        return
    CHUNK = 150
    done = len(vecs) - len(todo)
    for i in range(0, len(todo), CHUNK):
        batch = todo[i:i+CHUNK]
        cmd = [SOFFICE, '--headless', '--convert-to',
               f'png:draw_png_Export:{{"PixelWidth":{{"type":"long","value":{CANVAS_W}}},"PixelHeight":{{"type":"long","value":{CANVAS_H}}}}}',
               '--outdir', str(out_dir)] + [str(v) for v in batch]
        subprocess.run(cmd, capture_output=True, text=True, encoding='gbk', errors='replace', timeout=1800)
        done += len(batch)
        print(f'[step1] 进度 {done}/{len(vecs)}')
    ok = len([p for p in out_dir.glob('*.png')])
    print(f'[step1] 矢量图转换完成: {ok}/{len(vecs)}')
    return ok

def step2_sizes(docx: Path) -> dict:
    """media文件名 -> Word 显示尺寸 (pt)。VML(OLE公式) + drawingML(插图) 双通道。"""
    z = zipfile.ZipFile(docx)
    rels = z.read('word/_rels/document.xml.rels').decode('utf-8', 'ignore')
    rid2target = dict(re.findall(r'Id="(rId\d+)"[^>]*?Target="([^"]+)"', rels))
    docxml = z.read('word/document.xml').decode('utf-8', 'ignore')
    z.close()
    sizes = {}
    UNIT = {'pt': 1.0, 'in': 72.0, 'cm': 28.3465, 'mm': 2.83465}
    def parse_len(style: str, prop: str):
        m = re.search(prop + r':([\d.]+)(pt|in|cm|mm)', style)
        return float(m.group(1)) * UNIT[m.group(2)] if m else None
    # 通道A: VML (OLE 公式预览, 宽高单位可为 pt/in/cm/mm)
    for m in re.finditer(r'<v:(?:shape|rect|roundrect)\b[^>]*?style="([^"]*)"[^>]*?>(?:(?!</v:(?:shape|rect|roundrect)>).)*?<v:imagedata[^>]*?r:id="(rId\d+)"', docxml, re.S):
        style, rid = m.group(1), m.group(2)
        w, h = parse_len(style, 'width'), parse_len(style, 'height')
        base = os.path.basename(rid2target.get(rid, ''))
        if w and h and base:
            sizes[base] = (w, h)
    # 通道B: drawingML (插图, 单位 EMU, 1pt=12700EMU)
    for m in re.finditer(r'<w:drawing\b.*?</w:drawing>', docxml, re.S):
        blk = m.group(0)
        ext = re.search(r'<wp:extent cx="(\d+)" cy="(\d+)"', blk)
        rid = re.search(r'<a:blip r:embed="(rId\d+)"', blk)
        if ext and rid:
            base = os.path.basename(rid2target.get(rid.group(1), ''))
            if base:
                sizes[base] = (int(ext.group(1)) / 12700.0, int(ext.group(2)) / 12700.0)
    return sizes

def step3_build_assets(raw_dir: Path, media_dir: Path, final_dir: Path, sizes: dict):
    from PIL import Image, ImageChops
    final_dir.mkdir(parents=True, exist_ok=True)
    n_vec = n_png = n_fb = 0
    # 矢量图 (wmf/emf 产物): 裁边 + 2x retina
    for png in sorted(raw_dir.glob('*.png')):
        img = Image.open(png).convert('RGB')
        bg = Image.new('RGB', img.size, (255, 255, 255))
        bbox = ImageChops.difference(img, bg).getbbox()
        if bbox:
            x0, y0, x1, y1 = bbox
            m = 8
            box = (max(0, x0-m), max(0, y0-m), min(img.width, x1+m), min(img.height, y1+m))
            img = img.crop(box)
        src = png.stem + '.wmf'
        if src not in sizes:
            src = png.stem + '.emf'
        if src in sizes:
            w_pt = sizes[src][0]
        else:
            w_pt = 30.0
            n_fb += 1
        disp_w = round(w_pt * PT2PX)
        target_w = min(disp_w * 2, img.width)   # retina 2x, 不超原生渲染
        if target_w < 1:
            target_w = 1
        target_h = max(1, round(target_w * img.height / img.width))
        img = img.resize((target_w, target_h), Image.LANCZOS)
        img.save(final_dir / ('v' + png.stem + '.png'))
        n_vec += 1
    # 源生 PNG 插图: 原样复制
    for png in sorted(media_dir.glob('*.png')):
        shutil.copy2(png, final_dir / png.name)
        n_png += 1
    print(f'[step3] 资产就绪: 矢量 {n_vec} 个(其中尺寸回退 {n_fb}), PNG插图 {n_png} 个')

def step4_rewrite(md_path: Path, out_path: Path, media_token: str, ch_num: str, sizes: dict):
    md = md_path.read_text(encoding='utf-8')
    rel = f'/images/ch{ch_num}'
    n_md = n_html = 0
    def map_target(fname: str):
        """媒体文件名 -> (站点路径, 显示宽px或None)"""
        stem, ext = fname.rsplit('.', 1)
        ext = ext.lower()
        if ext in ('wmf', 'emf'):
            w_pt = sizes.get(fname, (30.0, None))[0]
            return f'{rel}/v{stem}.png', round(w_pt * PT2PX)
        return f'{rel}/{stem}.png', None
    # md 形式
    def repl_md(m):
        nonlocal n_md
        n_md += 1
        target, w = map_target(m.group(1))
        return f'![]({target})' + (f'{{width={w}}}' if w else '')
    md = re.sub(r'!\[\]\(' + re.escape(media_token) + r'/media/([^)]+)\)', repl_md, md)
    # html 形式
    def repl_html(m):
        nonlocal n_html
        n_html += 1
        fname, attrs = m.group(1), m.group(2)
        target, w_def = map_target(fname)
        wm = re.search(r'width:([\d.]+)in', attrs)
        if wm:
            w = round(float(wm.group(1)) * 96)
        else:
            w = w_def
        style = f' style="width:{w}px"' if w else ''
        return f'<img src="{target}"{style} alt="">'
    md = re.sub(r'<img src="' + re.escape(media_token) + r'/media/([^"]+)"([^>]*?)/?>', repl_html, md)
    out_path.write_text(md, encoding='utf-8')
    print(f'[step4] {out_path.name}: md引用 {n_md} 处, html引用 {n_html} 处')
    # 残留检查
    left = len(re.findall(re.escape(media_token) + r'/media/', md))
    if left:
        print(f'[step4][警告] 残留未重写引用 {left} 处!')
    return n_md + n_html

if __name__ == '__main__':
    total = 0
    for cn in sys.argv[1:]:
        num, title = CH[cn]
        print(f'===== ch{num} {title} =====')
        media = WORK / f'ch{cn}_media' / 'media'
        raw = WORK / f'ch{cn}_raw3x'
        final = ROOT / 'docs' / 'images' / f'ch{num}'
        step1_convert(media, raw)
        sizes = step2_sizes(ROOT / 'docx' / f'{title}.docx')
        (WORK / f'ch{num}_sizes.json').write_text(json.dumps(sizes, ensure_ascii=False, indent=1), encoding='utf-8')
        print(f'[step2] 显示尺寸 {len(sizes)} 个')
        step3_build_assets(raw, media, final, sizes)
        total += step4_rewrite(WORK / f'ch{cn}_docx.md', ROOT / 'docs' / f'ch{num}.md', f'ch{cn}_media', num, sizes)
    print(f'===== 批量完成, 共重写引用 {total} 处 =====')
