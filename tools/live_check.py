# -*- coding: utf-8 -*-
"""线上站点实测: 页面可达性 + 全部图片可访问性(并发 HEAD)

用法: python live_check.py [base_url]
默认 base_url = https://concretestructuredesign.readthedocs.io/zh-cn/latest
"""
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE = (sys.argv[1] if len(sys.argv) > 1 else
        'https://concretestructuredesign.readthedocs.io/zh-cn/latest').rstrip('/')
ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / 'docs'
IMG_REF = re.compile(r'(?:\]\(|src=")(/images/[^)"]+?)[")]')

PAGES = [''] + [f'/{p.stem}/' for p in sorted(DOCS.glob('ch*.md'))]

def fetch(url, method='GET'):
    req = urllib.request.Request(url, method=method,
                                 headers={'User-Agent': 'Mozilla/5.0 acceptance-check'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read(4096) if method == 'GET' else b''
    except urllib.error.HTTPError as e:
        return e.code, b''
    except Exception as e:
        return -1, str(e).encode()

def main():
    print(f'目标站点: {BASE}')
    # 1. 页面可达性
    for pg in PAGES:
        code, _ = fetch(BASE + pg + '/')
        tag = 'OK ' if code == 200 else 'FAIL'
        print(f'  [{tag}] {code} {pg or "/(首页)"}')

    # 2. 收集全部图片引用
    refs = set()
    for md in list(DOCS.glob('ch*.md')) + [DOCS / 'index.md']:
        refs.update(IMG_REF.findall(md.read_text(encoding='utf-8')))
    print(f'\n图片引用 {len(refs)} 张, 并发探测中...')

    fails = []
    with ThreadPoolExecutor(max_workers=24) as ex:
        futs = {ex.submit(fetch, BASE + r, 'HEAD'): r for r in sorted(refs)}
        for i, f in enumerate(futs.items(), 1):
            code, _ = f[0].result()
            if code != 200:
                fails.append((code, f[1]))
            if i % 200 == 0:
                print(f'  进度 {i}/{len(refs)}')

    print(f'\n图片探测完成: 成功 {len(refs)-len(fails)}, 失败 {len(fails)}')
    for code, u in fails[:20]:
        print(f'  [FAIL {code}] {u}')
    return 1 if fails else 0

if __name__ == '__main__':
    sys.exit(main())
