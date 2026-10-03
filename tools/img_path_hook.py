# -*- coding: utf-8 -*-
"""MkDocs 构建钩子：把站点根绝对图片路径改写为页面相对路径。

背景：文档源（docs/*.md）中的图片引用统一写作站点根绝对路径
（如 ``/images/ch04/vimage2.png``）。本地 `mkdocs serve` 站点挂在
域名根下，该写法有效；但 Read the Docs 把站点挂在子路径下
（如 /zh-cn/latest/），浏览器会把 ``/images/...`` 解析到子路径之外
导致全部 404。

本钩子在每页最终 HTML 产出后，把 ``"/images/`` 前缀改写为相对当前
页面深度的路径（章级页面 ``../images/``，根级页面保持 ``/images/``
不变——它在两种部署形态下均正确）。相对路径写法与部署根无关，
本地与 RTD 通用。
"""
import re

# 匹配紧跟在引号后的 /images/ 前缀（同时覆盖 src="..." 与 href="..."）
_ROOT_IMG = re.compile(r'(["\'])/images/')


def on_post_page(output: str, *, page, config, **kwargs) -> str:
    """按页面 URL 深度改写 HTML 中的根绝对图片路径。"""
    url = page.url or ''
    depth = url.count('/')
    prefix = '../' * depth
    if not prefix:
        # 根级页面（url 为空或 .html 文件名）：/images/ 在任何部署
        # 根下都指向站点根，无需改写。
        return output
    return _ROOT_IMG.sub(lambda m: m.group(1) + prefix + 'images/', output)
