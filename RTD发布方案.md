# 《混凝土结构设计原理》讲义发布至 Read the Docs 实施方案

> 状态：**规划稿（未执行任何转换、安装或部署操作）**
> 编制日期：2026-10-01
> 依据：对 9 个 docx 文件的**只读内部检查** + Read the Docs 官方配置规范（Configuration file reference, v2，已于 2026-10-01 核对）

---

## 1. 现状盘点（基于只读检查的事实）

检查方式：解包 docx（zip 容器）读取内部 XML 与媒体清单，**未修改任何文件**。

### 1.1 文件概况

| 章节 | 大小 | OLE 对象数 | 表格数 | 媒体文件 |
|---|---:|---:|---:|---|
| 第一章 混凝土结构材料的性能 | 36 KB | 0 | 0 | 0 |
| 第二章 混凝土结构设计方法 | 238 KB | 46 | 2 | WMF×34 |
| 第三章 轴心受力构件正截面承载力计算 | 541 KB | 21 | 0 | WMF×19, WDP×1, PNG×1 |
| 第四章 受弯构件正截面承载力计算 | 2.2 MB | 210 | 0 | WMF×177, WDP×2, PNG×6 |
| 第五章 受弯构件斜截面承载力计算 | 5.7 MB | 44 | 0 | WMF×41, PNG×9, EMF×1, WDP×9 |
| 第六章 受扭构件承载力计算 | 697 KB | 38 | 0 | WMF×37, PNG×1, WDP×1 |
| 第七章 偏心受力构件承载力计算 | 7.7 MB | 371 | 2 | WMF×251, WDP×8, PNG×8 |
| 第八章 裂缝、变形和耐久性 | 604 KB | 169 | 2 | WMF×141 |
| 第九章 预应力混凝土构件设计 | 1.5 MB | 299 | 5 | WMF×194, EMF×17 |
| **合计** | ≈19.7 MB | **1198** | **11** | **958** |

### 1.2 关键发现（决定本方案走向）

1. **原生 Word 公式（OMML）数量为 0**。全部 1198 个公式对象均为 OLE 嵌入对象，其 ProgID 分布为：
   - `Equation.AxMath`（AxMath 公式）：**1050 个**
   - `Equation.DSMT4`（MathType 6/7 公式）：**132 个**
   - `AxGlyph.Document`（AxGlyph 矢量插图）：15 个
   - `Visio.Drawing.15`（Visio 插图）：1 个
2. 每个 OLE 公式对象均带 **WMF 矢量预览图**（共约 890 个 WMF + 17 个 EMF），这是公式的"外观备份"，是兜底方案的资产。
3. AxMath 对象的 Contents 流经解析确认为**私有二进制格式**（非明文 LaTeX），无法直接提取源码；但 AxMath 软件本身支持 LaTeX 互转（见 §4 公式路线 A）。
4. 真实插图约 40–60 幅（PNG×25、WDP×21、EMF 若干、AxGlyph×15、Visio×1），需逐一处理格式兼容性。
5. 表格仅 11 个，量少，可人工精修。
6. 第一章为纯文本（无图、无公式、无表），可直接自动转换。

**结论：本项目最大的技术风险与工作量集中在"公式"环节（1182 个），插图次之，表格与文本最轻。**

---

## 2. 总体技术路线

```
docx（9 章）
   │  ① 公式预处理（三选一路线，见 §4，关键决策点）
   ▼
Pandoc 批量转换 ──► Markdown 源文件（9 个 .md）
   │  ② 后处理脚本（图片路径重写、命名规范化、标题层级校正）          ┐
   ▼                                                              │ 本地
MkDocs + Material 主题（含 MathJax 公式渲染、中文搜索）               │ 预览
   │  mkdocs serve 本地校对（逐章检查公式/图/表）                    ┘
   ▼
GitHub 仓库（GitHub Desktop 推送）
   ▼
Read the Docs 自动构建 ──► https://<项目名>.readthedocs.io
```

### 2.1 站点框架选型

| 方案 | 优点 | 缺点 | 结论 |
|---|---|---|---|
| **MkDocs + Material for MkDocs**（主推） | 配置极简、主题现代美观、原生支持 Markdown（Pandoc 输出对接零障碍）、MathJax 支持成熟、Read the Docs 官方一等公民 | 复杂交叉引用/公式自动编号能力弱于 Sphinx | **推荐**。本讲义为讲义型线性结构，无自动编号需求 |
| Sphinx + MyST-Parser（备选） | 学术文档标准、公式编号与交叉引用生态最强 | 配置复杂，学习成本高 | 仅当后续需要"按公式编号交叉引用"时再考虑 |

**给第一次接触者的说明**：MkDocs + Material 对新手反而更友好——(1) 您无需学习任何新语言，正文就是普通 Markdown（由 Pandoc 自动生成，您几乎不用动手写）；(2) 全部配置集中在一个约 40 行的 `mkdocs.yml`（由我准备维护）；(3) 本地预览一条命令、所见即所得；(4) 主题外观可先看官方演示站 **https://squidfunk.github.io/mkdocs-material/** 再决定。Sphinx 的优势（公式自动编号、复杂交叉引用）本讲义用不上；即便将来改变主意，内容源文件不变，迁移成本可控。

---

## 3. 所需软件清单

| 软件/组件 | 用途 | 状态（2026-10-01 实机核验） |
|---|---|---|
| **Pandoc 3.10** | docx → Markdown 转换核心 | ✅ 已安装 |
| **LibreOffice 26.2.6** | WMF/EMF/WDP → PNG/SVG 批量转换；公式路线 B 试验工具 | ✅ 已安装（`D:/Program Files/LibreOffice`，恰为方案推荐的 26.2 稳定版） |
| **MathType 7** | 公式批量转换（路线 A，处理 132 个 DSMT4 公式） | ✅ 已安装（`D:/Program Files (x86)/MathType`；与讲义公式格式完全匹配） |
| **Microsoft Word**（Office 16） | 承载 MathType 批量转换与文档自动化 | ✅ 已安装 |
| **Python 3.13** | MkDocs 构建链 | ✅ 已具备 |
| pip 包：`mkdocs` `mkdocs-material` `pymdown-extensions` `jieba` | 站点构建、主题、公式/中文搜索 | ⬜ 待装（由我装在独立虚拟环境内，不污染系统；国内网络慢时自动切换镜像源） |
| **Git 2.55 / GitHub Desktop** | 版本管理与推送 | ✅ 已安装（**待确认 GitHub Desktop 已登录您的账号**，发布阶段才需要） |
| **AxMath** | 公式批量转换（路线 A，处理 1050 个 AxMath 公式） | ⬜ 未安装（按既定策略：先 LibreOffice 试点，失败再装） |
| **VS Code** | 人工校对与修订 | ✅ 已安装 |
| Read the Docs 账号 | 托管平台 | ✅ 已注册 |

> **结论：您无需再安装任何软件。** 唯一待装的是站点构建用的几个 Python 包（由我在隔离虚拟环境中执行），以及视试点结果而定的 AxMath。所有转换与构建均可在本机完成，无需服务器。

---

## 4. docx → Read the Docs 兼容格式的转换思路

### 4.1 公式处置路线（**已定稿：路线 C**，2026-10-01 第四轮讨论拍板）

现状：1182 个公式全部是 AxMath/MathType OLE 对象，**Pandoc 无法将其识别为公式**（只会当作图片或丢弃）。

**决策记录**：
- 路线 B（LibreOffice 中转）试点结论：**失败**——第二章 46 个公式经 LibreOffice 转 ODT 后全部原样保留为 OLE 对象（MathML = 0），AxMath（1050 个）与 MathType DSMT4（132 个）均不被识别。
- 路线 C（图片保真）试点结论：**成功**——已建成全自动管线（`tools/pilot_ch02.py`）：WMF → 3 倍分辨率 PNG → 自动裁白边 → 按 Word 原始显示尺寸以 2 倍 retina 嵌入，第二章 34/34 公式全部通过，公式编号（如"(2-6)"）自动保留。
- **用户决策：采用路线 C，不再安装 AxMath、不动用 MathType。** 理由：图片与 docx 原版完全一致，不存在转换书写错误；零人工校对量。

~~路线 A（AxMath/MathType 批量转 LaTeX）~~ —— 已否决（无必要）；~~路线 B（LibreOffice 转 MathML）~~ —— 试点失败。以下为决策过程存档：

**路线 A（最优，需 AxMath/MathType）：软件内批量转换**
- 若本机装有 AxMath：用其 Word 加载项的**批量转换功能**，将全文档公式一次性导出为 LaTeX 文本（或 Word 原生公式 OMML）。
- 若本机装有 MathType：菜单 "Convert Equations…" 可将整篇文档公式批量转为 Word 原生公式或 LaTeX 文本（132 个 DSMT4 公式走此路径）。
- 转换后：Pandoc 可**无损**接管 OMML → LaTeX `$$...$$`，网页端由 MathJax 精美渲染，公式可复制、可搜索、无限缩放。
- 工作量：批量操作 + 抽查校对，约数小时。

**操作分工说明（涉及 MathType/AxMath 时的实际情况）**：
- 我可全自动完成：文档的打开/另存（Word COM 自动化）、Pandoc 转换、图片批量转换（LibreOffice 命令行无界面运行）、脚本后处理、建站与本地预览、Git/GitHub 操作。
- 需要您配合的：MathType/AxMath 的"批量转换"命令是在 Word 菜单里执行的对话框操作，**我无法无人值守遥控 GUI 软件**——但它是整篇文档一次性的批量命令，每章约 1–2 分钟、共约 15 分钟，我会提供逐步操作清单。
- **降依赖顺序（建议）**：先装 LibreOffice（反正是必需工具）→ 我用它试点第二章的 46 个公式（30 分钟出结论）→ 若可行，则 **AxMath 无需安装**；若不可行，再装 AxMath / 动用您已有的 MathType。

**路线 B（免费试验）：LibreOffice 中转**
- 用 LibreOffice Writer 打开 docx，另存为 ODT（LibreOffice 会将公式 OLE 导入为其内嵌公式），再由 Pandoc 读取 ODT，公式转 LaTeX。
- 优点：免费、全自动。**风险：对 AxMath（1050 个）与 MathType DSMT4（132 个）的导入兼容性未经验证，需 30 分钟试点即可得出结论。**
- 试点判定标准：以第二章 46 个公式为样本逐一比对，转换正确率 ≥95%（≥44 个）且 WDP/EMF 图片转换正常，视为路线 B 可行；否则启用路线 A。

**路线 C（兜底，保真降级）：公式按矢量图嵌入**
- 每个 OLE 公式均有 WMF 矢量预览图。批量提取全部 WMF → LibreOffice 转 SVG/PNG（2 倍分辨率）→ 以图片形式嵌入网页。
- 优点：**全自动、外观与 Word 版完全一致、零校对量**。缺点：公式不可复制、不可搜索、缩放渲染逊于 MathJax。

**推荐决策顺序：先确认 AxMath 可用性（A）→ 不可用则 30 分钟试点 B → 均不行则 C。**
亦可混合：重要章节（如第九章预应力公式推导密集）人工重录 LaTeX，其余走 C。

### 4.2 文本与结构转换（Pandoc 命令草案）

```bash
pandoc "docx/第二章 混凝土结构设计方法.docx" \
  -f docx \
  -t gfm+tex_math_dollars \
  --extract-media="docs/images/ch02" \
  --wrap=none \
  --markdown-headings=atx \
  -o "docs/ch02.md"
```

> 命令为草案，第一阶段试点时定稿（视公式路线可能改用 `-t markdown` 或先经 LibreOffice 中转）。

### 4.3 后处理（脚本自动化）

1. **图片路径与命名**：Pandoc 将图片导出至 `images/chNN/media/imageK.png`，脚本统一重写为 `images/chNN/fig-KK.ext` 并更新 Markdown 引用。
2. **标题层级**：Word 内"标题 1"→ Markdown `#`；若每章文件首标题需降级为页内 `#`、由 nav 承担章名，脚本统一处理。
3. **题注规范化**：Word 题注（"图 2-1 ×××"）转为图片下方居中斜体文字（Content 图注格式由 CSS 控制）。
4. **校对清单**：每章转换后按 checklist 逐项过——公式渲染、图片显示、表格完整性、脚注、交叉引用（"式(7-15)"等文字引用已固化，无断链风险但需抽查编号一致性）。

### 4.4 试点策略

- **第一轮试点（打通链路）**：第一章（纯文本，30 分钟内完成全链路验证）。
- **第二轮试点（暴露难点）**：第二章（46 个公式 + 2 表格，验证公式路线与表格质量）。
- **压力测试**：第七章（371 个公式、7.7 MB、全书最大）。
- 试点通过后再批量处理其余章节。

---

## 5. 图片、表格、公式的处理方式

### 5.1 图片（约 40–60 幅真实插图 + 公式预览图）

| 格式 | 数量 | 处理方式 |
|---|---:|---|
| PNG | ~25 | 直接使用；过大者压缩（目标单图 <300 KB） |
| WDP (HD Photo) | 21 | 浏览器不兼容，**必须转换**：LibreOffice/ImageMagick → PNG |
| EMF | ~18 | 浏览器不兼容，转 PNG 或 SVG |
| AxGlyph OLE | 15 | 优先用 AxGlyph 软件导出 SVG/PNG（矢量最佳）；否则用其 WMF 预览图转 SVG |
| Visio | 1 | 用 Visio 导出 PNG/SVG；无 Visio 则用 WMF 预览转换 |
| WMF（公式预览，路线 C 用） | ~890 | LibreOffice 批量 `--convert-to png/svg`，2 倍分辨率保证清晰度 |

统一规则：全部图片限制 `max-width: 100%` 响应式缩放；统一命名 `chNN-figKK`；第七章 7.7 MB 大文件须压缩以控制站点总体积。

### 5.2 表格（共 11 个）

- 简单表格：Pandoc 自动转 Markdown 管道表，Material 主题自带美观样式。
- **含合并单元格的表格**（工程表格常见，如材料分项系数表）：Markdown 管道表不支持跨行跨列，Pandoc 会退化为 HTML 表或拆分单元格。处理策略：**11 个表格全部人工核对**，复杂的直接改写为 HTML 表（MkDocs 原生支持嵌入 HTML），保留合并单元格效果。
- 宽表（超过 6–7 列）：CSS 设置横向滚动容器，避免移动端溢出。

### 5.3 公式（1182 个，**路线 C 定稿**：矢量图片嵌入）

- 全部公式以 WMF 矢量预览图为源，经 LibreOffice 转 3 倍分辨率 PNG、程序自动裁边、按 Word 原始尺寸 2 倍 retina 嵌入。**外观与 Word 版完全一致、零书写错误、零校对量**；代价：不可复制、不可搜索。
- 版式规则见 §5.4 网页排版规范。
- 校验要点（批量阶段抽查）：图片清晰度、行内小符号与文字基线对齐、公式编号完整。

### 5.4 网页排版规范（美观版式，**用户已确认的总原则**）

> 总原则：**不必逐字复刻 docx 的版式设置，以网页阅读美观为准**。以下为已实现的规范（`docs/stylesheets/extra.css` + `tools/layout.py` 后处理，9 章批量复用）：

| 排版项 | 规则 | 实现方式 |
|---|---|---|
| **字体** | 正文中文**仿宋**、各级标题**黑体**、所有西文 **Times New Roman**；字号保持 Material 默认不变（2026-10-02 用户确认） | CSS：`.md-typeset` 字体链 `"Times New Roman", FangSong`；`h1–h6` 字体链 `"Times New Roman", SimHei`（浏览器按字符自动分配：西文落 TNR、中文落仿宋/黑体） |
| **表格** | 表格整体**水平居中**（左右留白对称，无论表格宽度如何）；表名题注**居中**（黑体） | 后处理将每个表格包进 `<div class="tbl-wrap" markdown="1">`，CSS `flex + justify-content:center` 居中。**经验教训**：Material 的表格盒（`.md-typeset__table` inline-block + table `width:100%`）使 `margin:auto`、`text-align`、`display:table` 等常规居中在 Chrome 上全部失效（父级宽度依赖内容时 margin:auto 按规范解析为 0），flex 包裹是与盒模型解耦的可靠方案（2026-10-02 像素级验证：左右留白 163/164、113/113） |
| 正文段落 | 首行缩进 2 字符（中文排版习惯），标题/列表/表格/公式块/图注不缩进 | CSS `.md-typeset > p { text-indent: 2em }` |
| 独立公式段 | 公式**严格居中**，编号（如 (2-6)）**贴右对齐**——与 Word 讲义版式一致 | 后处理重写为 `<div class="eq">` 三区布局（公式居中 + 编号绝对定位贴右） |
| 行内公式/符号 | 与文字基线对齐，不撑行高 | CSS `vertical-align: middle` |
| 字体颜色 | **全黑**（docx 中的蓝色术语标注、红色重点标注一律转黑；Pandoc 输出默认即丢弃颜色，已验证无颜色残留） | 无需处理，天然达成 |
| 页内交叉引用 | Word 书签跳转（Pandoc 转为 `[文字](#锚点)` 链接，多数锚点失效且渲染为蓝色）**一律还原为纯文本黑字**；网页导航由侧边目录与搜索承担 | `tools/layout.py` 自动处理（试点两章共还原 14 处，构建断链警告归零） |
| 插图段 | 居中显示，不缩进 | CSS `.fig` 类（批量阶段应用） |
| 图注 | 居中、小号、灰色（"图 2-1 ×××"） | CSS `.fig-caption` 类（批量阶段应用） |
| 公式多图并排 | 同段多个公式图之间留适当间隙 | CSS `.eq img { margin: 0 .35em }` |
| 图片 | 响应式 `max-width: 100%`；**站根绝对路径 `/images/chNN/...`**（MkDocs 目录式 URL 下页面相对路径 `images/...` 会解析为 `/chNN/images/...` 导致 404，2026-10-02 已修复并截图验证） | CSS 全局 + `tools/layout.py` 路径规范化 |
| 章节导航 | 依 Word 标题 1–4 样式自动生成分级导航（试点已验证层级完全正确） | Pandoc 自动 + mkdocs nav |

后处理脚本 `tools/layout.py`（幂等可重跑）：自动识别"仅含公式图+编号"的段落重写为居中布局；行内混排公式保持原样；表名/图名行转题注；交叉引用链接还原；图片路径规范化为站根绝对路径。

**重要约束（用户要求，2026-10-02）**：原版 docx 文件内容**永不更改**——一切修改只发生在 `docs/` 下的转换产物；转换中发现的教材原文疑误（如 (2-16) 处"注：教材错了"批注文字）按用户指示处理，正文保持教材原样。

---

## 6. 项目目录与配置规划

### 6.1 目录结构（拟）

```
ConcreteDocs/
├── docx/                        # 原始 9 份 docx（入库存档，不参与构建）
├── docs/                        # 站点源文件（MkDocs 默认目录）
│   ├── index.md                 # 首页：课程简介 + 九章导航
│   ├── ch01.md ~ ch09.md        # 九章正文
│   ├── images/ch01/ ~ ch09/     # 各章插图（已转换、已重命名）
│   └── javascripts/mathjax.js   # MathJax 配置
├── mkdocs.yml                   # MkDocs 配置
├── requirements.txt             # RTD 云端构建依赖
├── .readthedocs.yaml            # Read the Docs 构建配置
├── .gitignore                   # 忽略 site/ 构建产物等
└── RTD发布方案.md               # 本方案文件
```

### 6.2 mkdocs.yml（核心配置拟稿）

```yaml
site_name: 混凝土结构设计原理
site_description: 《混凝土结构设计原理》课程讲义（共九章）
theme:
  name: material
  language: zh
  features:
    - navigation.tabs           # 顶部章节导航
    - navigation.top            # 返回顶部
    - content.code.copy
    - search.highlight
markdown_extensions:
  - pymdownx.arithmatex:
      generic: true             # MathJax 3 标准配置
  - tables
  - attr_list
  - admonition
  - pymdownx.superfences
  - toc:
      permalink: true
extra_javascript:
  - javascripts/mathjax.js
  - https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js
plugins:
  - search:
      lang: [zh, en]            # 中文搜索需 jieba 分词（已列入依赖）
nav:
  - 首页: index.md
  - 第一章 混凝土结构材料的性能: ch01.md
  - 第二章 混凝土结构设计方法: ch02.md
  - 第三章 轴心受力构件正截面承载力计算: ch03.md
  - 第四章 受弯构件正截面承载力计算: ch04.md
  - 第五章 受弯构件斜截面承载力计算: ch05.md
  - 第六章 受扭构件承载力计算: ch06.md
  - 第七章 偏心受力构件承载力计算: ch07.md
  - 第八章 裂缝、变形和耐久性: ch08.md
  - 第九章 预应力混凝土构件设计: ch09.md
```

### 6.3 .readthedocs.yaml（按官方 v2 规范拟稿，已核对 2026-10 版文档）

```yaml
version: 2
build:
  os: ubuntu-24.04
  tools:
    python: "3.13"
mkdocs:
  configuration: mkdocs.yml
python:
  install:
    - requirements: requirements.txt
```

### 6.4 requirements.txt

```
mkdocs>=1.6
mkdocs-material>=9.5
pymdown-extensions>=10.7
jieba
```

### 6.5 .gitignore

```
site/
__pycache__/
*.pyc
```

---

## 7. 发布到 Read the Docs 的步骤

> **发布形态与公开性（已核实官方政策，2026-10-01）**：Read the Docs 社区免费版**仅支持公开仓库，且文档对全世界公开**（官方 "Choosing between our two platforms" 页原文："Only supports public VCS repositories / All documentation is publicly accessible to the world"）；私有文档、认证访问属商业版功能（Business 计划，$50/月起）。**因此整个准备流程与"是否发布"完全解耦**：本地构建产出的是纯静态 HTML 网站（`mkdocs build` 的 `site/` 目录），最终可选：(a) 发布到 RTD 公开；(b) 打包 zip 校内分发 / 上传课程平台（不公开）；(c) 暂不发布、保持本地。发布与否、以何种形式发布，**可在全部准备完成后再定夺**；RTD 上线后亦可随时下线删除。

### 第 1 步：本地构建与预览
1. 在虚拟环境中 `pip install -r requirements.txt`。
2. `mkdocs serve` → 浏览器 http://127.0.0.1:8000 逐章校对（公式、图片、表格、搜索）。

### 第 2 步：建立 GitHub 仓库（GitHub Desktop）
1. GitHub Desktop → **File → Add Repository** → 选择 `D:\WorkbuddyProjects\ConcreteDocs` → 按提示创建本地仓库。仓库名严格译法二选一：`concrete-structure-design-principles`（直译）或 `principles-of-concrete-structural-design`（英文书名风格，常见教材命名法）。注意：仓库名只影响 URL 地址，站点页面标题仍显示中文《混凝土结构设计原理》。
2. 首次 **Commit**（提交全部文件）→ **Publish repository** 推送到 GitHub。**建议初建时选 Private**（GitHub 免费支持私有仓库，本地构建与预览完全不受影响），待确定发布 RTD 时再一键改为 Public（RTD 免费版要求公开仓库）——让"是否公开"的决策真正保留到最后。

### 第 3 步：Read the Docs 导入
1. 登录 https://readthedocs.org → **Add Project / 导入项目** → 授权 GitHub → 选择上述仓库。
2. RTD 自动检测根目录 `.readthedocs.yaml`，按其创建环境、安装依赖、执行 `mkdocs build`。
3. 构建完成后访问 `https://<项目名>.readthedocs.io`。

### 第 4 步：验证与设置
1. 检查九章导航、公式渲染、图片显示、中文搜索。
2. Dashboard → Admin → Versions：将 `latest`（对应 main 分支）设为默认版本。

### 第 5 步：日常更新流程（此后无需再碰 RTD 设置）
```
修改 docs/ 下 Markdown → GitHub Desktop: Commit → Push origin
→ Read the Docs 自动重新构建（约 1–2 分钟）→ 网站自动更新
```

> **讲义日后修订的维护方式**：若 docx 本身改版（换教材版本、增删例题），重跑一次转换脚本即可完成全套更新，无需手工重做；原始 docx 与转换脚本均在仓库中留档，全程可溯源。

---

## 8. 风险与注意事项

| # | 风险/事项 | 等级 | 应对 |
|---|---|:---:|---|
| 1 | **版权与公开性**：讲义若改编自出版教材（插图、例题、表格），在 RTD 公开传播需获得授权。已核实：RTD 社区免费版**仅支持公开仓库且文档全网公开**，无访问控制（私有文档属付费商业版） | **高（合规）** | 与发布解耦：本地准备完成后可选"打包 HTML 校内分发（不公开）"替代 RTD 发布；是否、何时、以何种形式发布由您最后定夺，RTD 上线后亦可随时删除下线 |
| 2 | ~~**公式转换质量**~~ **已消除**（路线 C 定稿）：公式以 WMF 预览图转高清 PNG 嵌入，与 docx 原版完全一致，不存在转换书写错误；试点 34/34 通过 | ~~高~~ → **低** | 见 §4.1 决策记录 |
| 3 | WMF/EMF/WDP 图片浏览器不兼容 | 中 | 全部批量转换为 PNG/SVG，脚本自动完成 |
| 4 | 合并单元格表格在 Markdown 中退化 | 中 | 11 个表格全部人工核对，复杂的改写 HTML 表 |
| 5 | 中文搜索分词质量 | 低 | jieba 已列入构建依赖；实测不满意可换 `zh.hans` 搜索方案 |
| 6 | RTD 构建限制（时长、产物体积） | 低 | 本项目约 20 MB 源、构建秒级，远低于平台阈值 |
| 7 | MathJax/主题资源经 CDN 加载，国内访问偶有波动 | 低 | 默认 jsdelivr CDN 在国内一般可用；如需可切换自托管 |
| 8 | Word 题注编号为固化文本（非自动域） | 低 | 实为优点：转出后编号稳定，不随 Word 域刷新错乱；增删图片时需手改编号 |
| 9 | 原始 docx 的版本管理 | 低 | 建议随仓库入库存档（共 19.7 MB，无需 LFS），保证可溯源、可回滚 |
| 10 | 第七章体积大（7.7 MB）导致页面加载慢 | 低 | 图片批量压缩，目标站点总体积 < 30 MB |

---

## 9. 分阶段执行计划（待您指令后启动）

| 阶段 | 内容 | 交付物 | 检查点 |
|---|---|---|---|
| **0 决策** | ~~确认公式路线~~ **已完成**：路线 C 定稿（2026-10-01）；版权与发布形态留待发布前定夺 | 路线决策 | ~~您确认~~ 已确认 |
| **1 环境** | ~~安装 Pandoc、LibreOffice；建虚拟环境装 MkDocs 链~~ **已完成**（含排版后处理工具 `tools/layout.py`） | 可用的工具链 | ~~汇报~~ 已汇报 |
| **2 试点** | ~~第一、二章转换，本地预览~~ **已完成并验收**（含 §5.4 排版规范实现） | 2 个章节页 | ~~您验收~~ 已验收 |
| **3 批量** | 其余 7 章转换（含第七章压力测试）+ 逐章校对 | 9 章全量源文件 | 汇报 |
| **4 站点** | mkdocs.yml 完善配置、首页、本地全站预览 | 本地可预览完整站点 | **您验收** |
| **5 发布** | GitHub 建仓推送 → RTD 导入构建 → 线上验证 | 在线网址 | 完成 |

**预估总工作量**：路线 A 约 1 个工作日（含校对）；路线 C 约 0.5 个工作日；路线 B 视试点结果介于两者之间。

---

## 附：讨论进展与待确认事项

**已议定（截至 2026-10-01 第四轮，试点完成）**：
1. **框架**：MkDocs + Material（您已确认满意）。
2. **仓库名**：`principles-of-concrete-structural-design`。
3. **软件环境实机核验完毕**：Pandoc 3.10、LibreOffice 26.2.6（D 盘）、MathType 7（D 盘，与讲义 DSMT4 公式格式完全匹配）、Word（Office 16）、Git 2.55、GitHub Desktop、VS Code、Python 3.13 均已就绪——**您无需再安装任何软件**。
4. **公式路线 C 定稿**（详见 §4.1 决策记录）：LibreOffice 试点失败（MathML=0），图片路线试点成功（34/34），您拍板采用 C——图片与 docx 完全一致零书写错误，AxMath 不装、MathType 不用。
5. **字体颜色全黑**：docx 中的蓝色术语、红色重点标注在网页版一律转黑（已验证 Pandoc 输出无颜色残留）。
6. **网页排版规范**（§5.4）：总原则"不逐字照搬 docx 版式，以网页美观为准"；已实现正文首行缩进 2 字符、独立公式居中+编号右对齐、行内公式基线对齐；插图/图注规则批量阶段应用。
7. **试点成果**：第一、二章已转换完成，本地站点构建通过（http://localhost:8000 预览），9 章批量转换的所有管线与脚本已就绪。

**仍待明确（均不阻塞批量转换）**：
1. **GitHub Desktop 是否已登录您的 GitHub 账号**（发布阶段才用，可到时再确认）。
2. **版权与发布形态**：本地准备完成后，"发布 RTD（公开）/ 打包 HTML 校内分发 / 暂不发布"由您最后定夺；建议仓库初建为 Private，发布时再改 Public。

*本方案仅为规划文件，未执行任何转换、安装或部署操作。收到您的明确指令后再启动实际工作。*
