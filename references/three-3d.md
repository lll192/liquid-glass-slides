# Three.js 3D 视觉能力 · 决策框架

本 skill 内置 Three.js 3D 视觉能力（库文件 `assets/three.min.js`，由 `scripts/build.py`
在**检测到 3D 场景时才内联**进最终单文件 HTML）。本文档规定「何时加、加什么效果、
放哪、如何保持风格一致」，确保 3D 真正增强主题表达与视觉冲击，而非炫技噪音。

> **首要原则：宁可少加，不可硬加。** 只给「氛围页 / 关键概念页」加 3D；纯信息页
> （bullets / grid-cards / timeline / comparison / two-column / chart）一律不加。
> 每页都加会稀释冲击力，且违背本 deck 的克制美学。

> **完全自动：** 下面的 `three` 字段是 AI 与 build.py 之间的接口，**用户从不手写**。
> 用 PPT skill 时，AI 自动扫描每页、判断该加哪种场景、写进 outline、一键构建，
> 用户零代码、零复制。

## 1. 实现机制（为什么可靠）

- **全局唯一画布**：所有 3D 渲染在 `#lg-three` 这一个 `<canvas>` 上，固定定位在
  背景光斑（`.bg`）与正文（`.slide-content`）之间，`pointer-events:none`，**永远在文字背后**，
  绝不和正文抢位置——从根上避免「挤文字」问题。
- **单 WebGL 上下文**：用 `IntersectionObserver` 监听当前可见 slide，切到哪一页就加载
  该页的 Three.js 场景；不会「每页一个 canvas」导致超出浏览器 ~16 个 WebGL 上下文上限。
- **按需内联**：只有 outline 出现 `three` 字段时，才把 `three.min.js` + 初始化脚本嵌进 HTML；
  普通 deck 仍是零依赖小文件。
- **尊重无障碍**：`prefers-reduced-motion: reduce` 时只渲染一帧静态画面，不做动画。

## 2. 何时加（扫描每一页后判断）

**应该加（信号）**
- 封面（cover）：需要第一眼的「空间纵深感」与品牌氛围。
- 章节分隔（section-divider）：每个大章节开头，用粒子场铺垫进入新主题的仪式感。
- 关键概念页 / 收尾页（closing）：主题升华处，用玻璃实体或星云强化记忆点。

**不应该加（信号）**
- 纯信息页：bullets / grid-cards / kpi-grid / comparison / two-column / timeline /
  stat-highlight / chart —— 内容本身已清晰，加 3D 只会增加噪声、拖慢性能。
- 一页已有大图（hero）又要在同一处加实体 → 二选一，避免视觉打架。

## 3. 场景类型速查（build.py 内置预设，共 7 种）

| 预设 `scene` | 效果 | 适用 | 主题气质 |
|---|---|---|---|
| `field` | 缓慢漂浮的彩色柔光点（bokeh，低透明度） | 封面 / 章节分隔 / 氛围背景，最通用、最安全 | 中性 |
| `nebula` | 更密、更快的粒子星云，冲击更强 | 规模 / 增长 / 生态类主题，需要「哇」一下时 | 科技 / 数据 |
| `object` | 缓慢自转的半透明线框多面体 + 实体层，默认偏右 | 结构 / 机制 / 核心概念页 | **偏理工**——人文/文学/历史主题慎用 |
| `network` | 节点 + 连线的关系网（缓慢自转） | **仅限内容本身就是关系/网络/生态**的页；不要压在普通文字页上（散点会像污渍） | 科技 / 数据 |
| `petals` | 拉长柔光「花瓣」缓缓下落 + 横向摆动 | 文学 / 历史 / 人文 / 自然 / 抒情氛围页 | 人文 / 诗意 |
| `orbs` | 少量大型半透明玻璃气泡缓缓浮动 | 梦幻 / 哲思 / 盛宴 / 留白多的分隔页 | 轻盈 / 梦 |
| `waves` | 4 条彩色正弦波线层叠起伏 | 叙事流 / 时间 / 情绪流等抽象母题 | 抽象 / 优雅 |

### 3.1 按主题气质选型（AI 必读）

先判主题，再选预设，**气质不符的预设一律不用**：

- **人文 / 文学 / 历史 / 艺术**（如《红楼梦》、诗词、美学）：首选 `petals`、`orbs`、`waves`；
  慎用 `object`（线框几何有强烈「数学/科技」暗示）与 `network`（散点易像噪点）。
- **科技 / 数据 / 工程**：`field`、`nebula`、`object`、`network` 均可。
- **拿不准时**：`field` 最安全。
- 同一 deck 内 3D 预设不宜超过 3 种，保持视觉语言统一。

### 3.2 `object` 形状可选

`scene` 支持带参写法 `"object:形状"`，形状取值：`icosahedron`（默认）| `dodecahedron` | `torusKnot` | `torus` | `sphere`。
例如 `{ "three": { "scene": "object:torusKnot" } }`。

> 所有预设配色自动取自 deck 主题色（outline.theme.colors），
> 浅色、柔和、慢动，与液态玻璃风格天然一致。粒子在浅底上以 **NormalBlending + 生成式柔光 sprite**
> 呈现为柔和彩色形状（而非加色混合——加色在白底会被洗白、几乎看不见），保证在浅色主题下清晰可读。

## 4. 放置位置

- 3D **永远在文字背后**（z-index 介于光斑与内容之间），不另开布局、不挤占正文。
- `object` 预设已默认偏右（camera.x≈2.6），适合左侧有文字、右侧留白的页面；
  若落在居中文字页，务必确认透明度足够低、或改用 `field`/`nebula`。
- 窄屏 / 低端机：WebGL 仍会渲染，但粒子数已控制；如担心性能，优先少量页使用。

## 5. outline 写法（AI 参照，用户无需关心）

```json
{ "layout": "cover", "title": "Lean 形式化证明", "three": { "scene": "field" } }
{ "layout": "section-divider", "num": "01", "title": "什么是 Lean", "three": { "scene": "field" } }
{ "layout": "section-divider", "num": "02", "title": "核心机制", "three": { "scene": "object" } }
{ "layout": "stat-highlight", "num": "100", "unit": "万行", "title": "Mathlib 代码体量", "three": { "scene": "nebula" } }
{ "layout": "closing", "title": "让机器成为你的证明搭档", "three": { "scene": "nebula" } }
```

- `scene` 取值：`field` | `nebula` | `object[:形状]` | `network` | `petals` | `orbs` | `waves`。
- 不写 `three` 字段的页：画布对该页透明，仅显示 CSS 光斑背景。

## 5.1 背景装饰字形（glyphs）随主题走

`deck` 背景的 3 个大号漂浮字符（glyphs）**不再硬编码**，由 outline 顶层 `glyphs` 字段提供
（最多 3 个单字，按 g1/g2/g3 槽位渲染；颜色/字号沿用模板样式，自动取主题色）：

```json
{ "title": "红楼梦", "glyphs": ["夢", "玉", "詩"], ... }
{ "title": "Lean 形式化证明", "glyphs": ["π", "∑", "∫"], ... }
```

- **选字规则**：取与主题强相关的单字或符号（学科符号、关键字、艺术字符如 ✦❋）；
  人文主题用汉字关键字，理工主题用学科符号。
- 不写 `glyphs` 字段 → 背景不显示任何字符（留空），绝不出现与主题无关的默认符号。

## 6. 自检清单

- [ ] 该页是否真的属于「氛围 / 关键概念」类，而非纯信息页？（否 → 不加）
- [ ] 选的场景是否与页面分量匹配？（普通分隔用 field；升华点用 nebula/object）
- [ ] `object` 是否避开了居中文字？是否留足留白？
- [ ] 全 deck 3D 页是否「克制」（不是每页都加）？
- [ ] 重建后 `grep -c 'lg-three'` ≥ 2（canvas 元素 + 初始化），且 `three.min.js` 仅在用到时内联。
