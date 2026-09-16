# Image Handling — 图片接入与处理规范（用户传入 + AI 生成）

本 skill 的成品是**单一自包含 HTML 文件**（内联 CSS/JS、零外部依赖），所以任何图片都必须以 base64 内联，**查看时不存在外部文件系统**。本文统一规定如何接收、透明化、嵌入、缩放、摆放图片——无论图片是 AI 生成的（另见 `prompt-patterns.md`），还是**用户自己提供的**。

## 1. 接收（用户传入图片）
- 支持的格式：PNG、JPG/JPEG、WebP、SVG。（BMP/TIFF：先转格式。）
- 优先要主体清晰、且背景透明或纯色（对象 / logo / 产品图）。
- 照片（复杂背景）也可以用，但必须"装框"摆放（见 §4），**不要悬浮**。
- 拿到图片后先确认尺寸与是否带透明通道，再决定处理方式。

## 2. 透明化归一（最关键的一步）

> **一句话决策原则（嵌入前的首要判断）**
> - 图片**背景透明 / 已抠好 / 纯白底可转透明（logo、产品、主图对象）** → 走 **透明对象悬浮** 方式：`.hero-orb` / 分栏球，无框、无圆角、`filter:drop-shadow(...)` 浮起，必须像浮在页面上。
> - 图片**带有真实/复杂背景（照片类）** → 走 **同心圆角玻璃相框** 方式：`.glass` 卡片包裹，见 §4b（`height` 限高 + `width:auto` 贴合 / `object-fit:cover` + `border-radius:calc(var(--r)*.64)`），**绝不**无框悬浮。
> - **AI 生成的图片同样适用本原则**：生成前先想清楚它要怎么摆——要做悬浮对象，就**主动要求生成透明 / 纯白背景**（便于转真透明，见下方转 alpha 流程）；要做玻璃相框，就直接生成带场景 / 照片式背景。不确定用户想要哪种摆法时，**主动询问**，不要默认一种了事。
> 拿不准就判断：主体是否干净、可脱离背景独立存在？可独立→悬浮；不可独立→装框。

摆放前先判断背景属于哪一类：

- **本身有真透明通道（透明 PNG / SVG）** → 直接用。可悬浮（`.hero-orb` / 分栏球）或内联。
- **纯色 / 白色背景（logo、白底产品图，或 AI 渲染回来是 RGB 白底的）** → 把白底转成真透明，让对象"无框悬浮"。
  - 检测：用 Pillow 打开，看四角像素。若 `mode` 无 alpha 且四角接近纯白 → 白底。
  - 逐像素转换：`a = 255 - min(r,g,b)`；再从白底反解前景色：`c' = (c - (255-a)) / a * 255`，clamp 到 0–255。这样主体内部的半透明质感保留，四周白底消失。
  - 转换后验证四角 alpha 已为 0。
- **照片（丰富背景）** → **不要抠底**。放进毛玻璃卡片里（`height` 限高 + `width:auto` 贴合，见 §4b），不要无框悬浮。

## 3. 嵌入（强制）
- 一律以 base64 data URI 内联：`<img src="data:image/png;base64,...">`。**不允许外部 URL、不允许相对文件路径**——HTML 必须能独立打开。
- 控制内联总体积（见 §6 优化）。

## 4. 摆放模式
| 模式 | 适用 | 类 / 技法 |
|---|---|---|
| 全屏背景 | 氛围图 / 封面背景 | `.bg` 图层，`opacity` 降低，可重模糊 |
| 悬浮对象（透明） | logo、产品、玻璃主图（**仅限背景透明的对象**） | `.hero-orb` + `filter:drop-shadow(...)`，无边框无圆角，必须像浮在页面上 |
| 悬浮照片卡（变体） | 用户喜欢"浮起感"的照片 | 无玻璃框，但**必须**带圆角 + 柔和投影（如 `border-radius:18px` + `drop-shadow`）。它本质是"卡"，不是透明对象；纯无处理的矩形照片悬浮仍是反模式 |
| 玻璃装框照片 | 任意照片 | `.glass` 卡片包裹 `<img>`，`height` 限高 + `width:auto` 贴合（或 `object-fit:cover`），见 §4b |
| 内联内容图 | 文字间的示意图 | `<img>` 居中，`object-fit:contain`，限制 `max-height` |

## 4b. 同心圆角（装框类铁律）
嵌图进任何框（玻璃卡 / 悬浮卡）时，圆角必须**同心**：
`内图圆角 = 外框圆角 − 内边距`。推荐用 CSS 变量一次算好：

```css
.frame{ --r:clamp(20px,2.6vw,28px); border-radius:var(--r); padding:calc(var(--r)*.36); }
.frame img{ border-radius:calc(var(--r)*.64); } /* .64 + .36 = 1，天然同心 */
```

**相框必须收缩贴图（严禁大框小图）**：
- 框宽一律 `width:fit-content`（或 `inline-block` 收缩包裹），**禁止**写死 `width:min(88vw,560px)` 之类的定宽——图按 `height` 缩放后窄于框，左右会留出一大截空玻璃，比例失衡。
- 图片四周露出的玻璃边 = `padding`，四边天然均匀（就长出边缘一点点，≈10px）。
- 防溢出上限只写在 `max-width`（如 `max-width:min(92vw,640px)`），超宽图由 `object-fit:cover` 裁切兜底。

禁止外框大圆角、内图小直角的错配（视觉上会"拧巴"）。

**前置条件（易踩坑）**：`border-radius` 切的是 **img 元素框**，不是照片本体。
- 若用 `object-fit:contain` + `max-height`，照片被限高后会在框内 **letterbox**（左右留白），元素框圆角落在留白上——**照片看起来仍是直角**。
- 正确做法二选一：
  1. `width:auto; height:min(52vh,460px); max-width:100%; object-fit:cover` → 元素框贴合照片本体，完整显示、圆角切到照片（推荐）；
  2. `width:100%; height:min(52vh,460px); object-fit:cover` → 照片填满元素框，轻微裁切、圆角切到照片。
- 验收标准：**截图放大看四角，照片本体必须呈现圆角**。

## 5. 缩放（绝不撑破视口）
- 所有 `<img>`：模板基础已设 `max-width:100%`、`max-height:min(52vh,460px)`、`object-fit:contain`。
- 主图 / 悬浮对象：宽度不超过 `min(40vw,340px)`。
- 任何图片都不得超过单页 `100dvh`；本 deck 基础禁止页内滚动。

## 6. 优化（嵌入前）
用 Pillow 控制单文件体积：
- 长边 ≤ 1600px（封面 / 主图）或 ≤ 1200px（内联图）。
- 重编码：PNG → `optimize=True`；照片 → 转 WebP 或 JPEG quality 85。
- 目标每张 ≤ ~300–500 KB；含 2–3 张图的 deck 总大小控制在 ~3 MB 以内。
- 同一张图重复出现（如封面和结束页都用 logo）→ 只嵌入一次，两处引用同一 data URI。

## 7. 反模式（禁止）
- 禁止把"必须阅读的文字"烤进图片（文字一律用 HTML）。
- 禁止引用外部图片 URL 或本地文件路径。
- 禁止给复杂背景的照片做无框悬浮（会像贴上去的）。
- 禁止让图片触发页内滚动条。

## 8. 可复用代码片段（白底 → 透明）
```python
from PIL import Image
img = Image.open(src).convert('RGB'); px = img.load(); w, h = img.size
out = Image.new('RGBA', (w, h)); op = out.load()
for y in range(h):
    for x in range(w):
        r, g, b = px[x, y]
        a = 255 - min(r, g, b)
        if a == 0:
            op[x, y] = (0, 0, 0, 0)
        else:
            rr = round(max(0, min(255, (r - (255 - a)) * 255 / a)))
            gg = round(max(0, min(255, (g - (255 - a)) * 255 / a)))
            bb = round(max(0, min(255, (b - (255 - a)) * 255 / a)))
            op[x, y] = (rr, gg, bb, a)
out.save(dst)
```
