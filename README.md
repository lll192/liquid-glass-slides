# Liquid Glass Slides · 液态玻璃幻灯片

> 一个面向多种 AI 编程与智能体环境的演示文稿生成 Skill：把文章、大纲、笔记、Markdown 或零散想法，一键生成 **Apple iOS 26 液态玻璃（Liquid Glass）风格** 的动画 HTML 幻灯片。

[English version below ↓](#english)

## 这是什么

`liquid-glass-slides` 是一个模型无关、可移植的演示文稿生成技能。它既可安装到 WorkBuddy 或支持 `SKILL.md` 的智能体环境，也可通过仓库内置适配文件在 OpenAI Codex、Claude Code、Gemini CLI 与 Cursor 中直接使用。任何能够读取 Markdown 并运行 Python 的 AI Agent，也可以遵循 `references/INSTRUCTIONS.md` 完成同样的构建流程。

- **液态玻璃质感**：半透明磨砂面板、背景虚化与折射、边缘高光、层次景深，忠实还原 Apple 的 Liquid Glass 设计语言（纯 CSS 实现，无原生 Apple API）。
- **构成主义简约版式**：默认采用非对称网格、严格边缘对齐、尺度对比与大留白；用一个共享玻璃平面组织内容，避免“每句话一张卡片”的仪表盘感。
- **智能构图与密度检测**：根据项目数量、左右文字量和页面类型自动选择 7:5 / 5:7、主次网格、马赛克网格及图文方向；内容过载时明确警告，不再无止境缩小字号。
- **中文与中英混排优化**：按视觉长度自动区分短、中、长标题，启用中文严格换行、标题平衡换行、脚本感知字距和表格数字，并提示需要改写的超长标题。
- **图片与图表智能编排**：识别横图、竖图、方图及趋势、比较、占比、雷达、分布图，自动调整图文比例和图表高度，并检查替代文本与数据结论。
- **整套节奏与自动质检**：构建时发现连续重复版式、页面重量失衡和缺失的呼吸页；浏览器端无需截图即可检测溢出、越界、标题过度换行和过小字号。
- **文案与演讲备注分层**：识别空泛标题和过长屏幕文案，用 `main_point` 固定每页核心结论，用 `speaker_notes` 保存约 100 字的自然讲稿；播放时按 `N` 可直接编辑并自动保存到本机浏览器。
- **Narrative Director**：为每页规划故事角色、观众问题、讲述意图、情绪节拍和自然转场；演讲者视图只保留核心结论与转场提示，并检测连续平铺、缺少证据或反差的故事弧。
- **Visual Coverage Planner**：区分“解释信息的视觉”与纯装饰，规划图片、图表、数据表、流程图和概念图；检测视觉缺失、连续纯文字页与图表/表格来源缺失。
- **真实中文文字**：所有可读文字都是真正的 HTML 文本，绝不乱码、可直接编辑。
- **零依赖单文件输出**：内联 CSS/JS，浏览器直接全屏播放，支持键盘 / 滚轮 / 触摸翻页与入场动画。
- **ECharts 数据图表**：仅在页面确有真实可比数据时自动加入（趋势、对比、占比、雷达），并自动套用液态玻璃主题。
- **Three.js 动态背景**：封面可使用粒子或星云；非封面仅在内容语义需要时使用关系网、花瓣或波形（单共享画布，按可见页切换）。
- **自动涟漪兜底**：页面没有 Three.js、ECharts 或图片时，构建器自动加入克制的涟漪材质；信息密集页使用静态低对比纹理，稀疏页面可使用轻微动态。
- **主题色自动系统**：根据主题自动派生 3 个背景晕染色 + 粒子色 + 1 个强调色，正文保持近黑以保证可读性。
- **可选 AI 配图**：封面 / 章节分隔可自动生成透明背景的装饰插画（仅用于装饰，文字绝不进图）。
- **生成前 Brief Gate**：先盘点用户已经提供的信息；信息不足时一次性显示 6 项简洁表单，信息充分时直接生成结构化简报，避免重复追问。
- **可复用设计简报**：把主题、目标、受众、内容归属、视觉偏好和约束固化为可校验的 `brief.json`，再进入故事板与渲染。
- **条件式 Source Gate**：选择完整文案或部分素材时，支持附件、本地路径、粘贴文本及图文混合上传，自动确认主文案、辅助材料、图片用途、改写幅度和缺失内容。
- **来源与补写可追踪**：通过 `source-manifest.json` 和 `content-map.md` 区分用户原文、辅助参考与 AI 补充，避免素材混用或静默改写。
- **稳定 Deck Protocol v2**：用永久 `deck_id` 与唯一 `slide_id` 绑定页面、笔记和后续修改；提供标准库校验器、机器可读 JSON Schema 与旧版确定性迁移工具。
- **可恢复生产流水线**：一次运行生成故事板、视觉规划、HTML、QA 报告与任务状态；失败会记录精确阶段和错误，修正后可由同一或另一个 AI 继续执行。
- **Content Director 内容导演**：自动输出逐页叙事、演讲备注、屏幕文案和信息视觉诊断；仅安全补全结构元数据，不擅自改写事实。
- **统一 Agent CLI**：Codex、WorkBuddy、Claude、Gemini、Cursor、自动化脚本与未来 MCP 统一调用 `scripts/slides.py`；JSON 返回结构和退出码稳定，不再解析终端文案。
- **本地 MCP 工具服务器**：支持 MCP 的 AI 可直接发现并调用 6 个 `slides_*` 工具，同时读取协议、说明和布局资源；所有文件访问限制在启动时指定的工作目录内。
- **安全 HTTP API**：网页、自动化平台和远程智能体可通过 Bearer Token 调用同一生产内核；默认仅监听本机，并提供 OpenAPI 3.1 描述。
- **本地生产控制台**：无需编写命令即可选择大纲、验证、快速构建、运行完整流水线、查看错误与警告，并在同一页面预览成品。

## 快速开始

### 路径 B：一键生成（推荐，可复现）

1. 根据 `references/intake.md` 完成生成前 Brief Gate，生成 `brief.json`（示例见 `examples/sample-brief.json`）。
2. 校验简报：
   ```bash
   python scripts/slides.py --json validate brief.json
   ```
3. 如果使用完整文案或部分素材，根据 `references/source-intake.md` 生成并校验来源清单：
   ```bash
   python scripts/slides.py --json validate source-manifest.json
   ```
   纯 AI 策划且没有附件时跳过此步。
4. 根据简报和内容覆盖表编写 v2 `outline.json`，为整套演示设置稳定的 `deck_id`，并为每页设置唯一 `slide_id`（字段规范见 `references/outline-schema.md`、`references/deck-schema-v2.json` 与 `examples/sample-outline.json`）。
5. 校验并构建：
   ```bash
   python scripts/slides.py --json validate my-talk.json
   python scripts/slides.py --json build --outline my-talk.json --out my-talk.html
   ```
   仅依赖 Python 标准库，无需联网（AI 配图除外）。输出一个自包含 HTML 文件。

旧版 outline 可以先迁移：

```bash
python scripts/migrate_outline.py old-outline.json --out outline-v2.json
```

### 生产流水线（推荐给多 AI 与持续迭代项目）

```bash
python scripts/slides.py --json run \
  --brief brief.json \
  --source-manifest source-manifest.json \
  --outline my-talk.json \
  --out dist/my-talk.html
```

如果没有外部文案，可省略 `--brief` 和 `--source-manifest`。流水线会在 HTML 旁生成：

- `my-talk.storyboard.json`
- `my-talk.visual-plan.json`
- `my-talk.director-report.json`
- `my-talk.qa-report.json`
- `my-talk.pipeline-state.json`

查看状态：

```bash
python scripts/slides.py --json status dist/my-talk.pipeline-state.json
```

### 路径 A：手写（创意 / 探索）

从 `assets/template.html` 或 `templates/deck.html` 起步，克隆 `<section class="slide">` 块，填充真实 HTML 文本。完整工作流见 `SKILL.md`。

## 多 AI / 跨平台使用

本仓库的模型无关工作流统一放在 [`references/INSTRUCTIONS.md`](references/INSTRUCTIONS.md)。`SKILL.md` 提供可安装的 Skill 入口，其余平台通过各自的仓库级适配文件加载相同规则：

| 平台 | 加载文件 | 说明 |
|---|---|---|
| **WorkBuddy / Skill-compatible agents** | `SKILL.md` | 可安装 Skill 入口（含 frontmatter） |
| **OpenAI Codex** | `AGENTS.md` | 仓库级指令；安装为个人 Skill 时同样可使用 `SKILL.md` |
| **Claude Code** | `CLAUDE.md` | 打开仓库时加载；也可复制为 Claude Skill |
| **Gemini CLI** | `GEMINI.md` | 同上 |
| **Cursor** | `.cursor/rules/liquid-glass-slides.mdc` | 命中 `.json` 时触发 |
| **其他 AI Agent** | `references/INSTRUCTIONS.md` | 读取模型无关说明，并调用同一个 Python 构建器 |

所有平台统一的入口命令（零依赖、无需联网）：

```bash
python scripts/slides.py --json doctor
python scripts/slides.py --json build --outline my-talk.json --out my-talk.html
```

支持 MCP 的客户端可直接启动本地工具服务器：

```bash
python scripts/mcp_server.py --workspace C:/path/to/presentation-project
```

配置示例和安全边界见 [`references/mcp-server.md`](references/mcp-server.md)。

网页或自动化平台可启动本地 HTTP API：

```bash
python scripts/api_server.py --workspace C:/path/to/presentation-project
```

打开终端显示的 `http://127.0.0.1:8765` 即可进入生产控制台，把同一窗口里的 Bearer Token 粘贴一次完成连接。服务器仍可供其他网页或自动化平台调用；接口说明见 [`references/http-api.md`](references/http-api.md)，控制台说明见 [`references/production-console.md`](references/production-console.md)。

## 目录结构

```
liquid-glass-slides/
├── SKILL.md                 # 技能说明与工作流
├── LICENSE                  # MIT
├── README.md                # 本文件
├── assets/
│   ├── engine.css           # 玻璃系统 / 动画 / 基础样式
│   ├── engine.js            # 翻页控制器（键盘/滚轮/触摸）
│   ├── template.html        # 手写起步脚手架
│   ├── theme-tokens.json    # 设计令牌
│   ├── echarts.min.js       # 图表库（按需自动内联）
│   └── three.min.js         # 3D 库（按需自动内联）
├── templates/
│   ├── deck.html            # 构建骨架
│   └── single-page/         # 18 个布局片段（含 chart/data-table/process-flow/concept-map）
├── scripts/
│   ├── validate_brief.py    # 设计简报校验器（仅标准库）
│   ├── validate_source_manifest.py # 素材来源校验器（仅标准库）
│   ├── validate_outline.py  # v2 Deck Schema 与稳定 ID 校验器
│   ├── migrate_outline.py   # 旧版 outline → v2 确定性迁移
│   ├── pipeline.py          # 可恢复的多阶段生产流水线与任务状态
│   ├── content_director.py  # 逐页内容诊断与安全元数据补全
│   ├── slides.py            # 统一 Agent CLI 与稳定 JSON 调用协议
│   ├── agent_service.py     # CLI / MCP / HTTP 共享服务边界
│   ├── mcp_server.py        # 零依赖 MCP stdio 工具服务器
│   ├── api_server.py        # 带认证和工作目录隔离的 HTTP API
│   └── build.py             # 一键构建器（仅标准库）
├── console/                 # 零依赖本地生产控制台
├── references/              # 各模块参考文档
└── examples/                # 示例 outline 与成品
```

## 许可证

[MIT](LICENSE) © 2026 lll192

---

<a id="english"></a>
# Liquid Glass Slides (English)

A model-agnostic presentation-generation **Skill** that turns articles, outlines, notes, Markdown, or rough ideas into **Apple iOS 26 Liquid Glass style** animated HTML slide decks. It works as an installable skill in compatible agent environments and includes repository adapters for OpenAI Codex, Claude Code, Gemini CLI, and Cursor.

## Highlights

- **Liquid Glass aesthetic** — translucent frosted panels, backdrop blur/refraction, specular edge highlights, layered depth (pure CSS, no native Apple APIs).
- **Constructivist-minimal composition** — asymmetric grids, strict edge alignment, scale contrast, quiet space, and shared glass planes instead of dashboard-like card repetition.
- **Layout intelligence and density checks** — automatically selects split direction, feature-first or mosaic grids, media side, and bounded compact spacing; overfull slides are reported for revision instead of silently shrinking text.
- **Editorial CJK and mixed-script typography** — visual-length title profiles, strict Chinese line breaking, balanced headings, script-aware tracking, tabular figures, and warnings for titles that should be rewritten.
- **Visual intelligence** — profiles landscape/portrait/square imagery and trend/comparison/proportion/radar/distribution charts, then adjusts visual ratios and bounded chart height while checking alt text and takeaways.
- **Deck rhythm and automatic QA** — reports repetitive layout/weight sequences at build time, then measures overflow, boundaries, title wrapping, and minimum readable type in the real browser viewport without routine screenshot loops.
- **Content and presenter-note intelligence** — flags generic titles and oversized display blocks, preserves one `main_point` per page, and keeps natural, page-specific `speaker_notes` in an editable, locally auto-saved `N`-toggle presenter panel.
- **Narrative Director** — plans story roles, audience questions, speaker intent, emotional beats, and transitions; the live panel keeps only the main point and transition while flat story arcs are reported.
- **Visual Coverage Planner** — distinguishes explanatory visuals from decoration, plans images/charts/tables/flows/maps, and reports missing required visuals, provenance, or long text-only runs.
- **Real, editable text** — all readable text is genuine HTML; Chinese never garbles.
- **Zero-dependency single file** — inlined CSS/JS, fullscreen playback, keyboard/wheel/touch navigation with reveal animations.
- **ECharts charts** — auto-added only where real quantitative data exists, themed to match the deck.
- **Three.js motion backgrounds** — particles or nebula on covers, with network, petals, or waves reserved for semantically relevant non-cover pages (one shared canvas, swapped by visible slide).
- **Automatic ripple fallback** — slides without Three.js, ECharts, or imagery receive a restrained ripple material automatically; dense layouts use a quiet static treatment.
- **Auto color theme** — 3 background blobs + particle colors + 1 accent derived from the topic; body text stays near-black.
- **Optional AI imagery** — transparent decorative hero/motif illustrations (text never baked into images).
- **Web image sourcing** — searches reusable photography, archives, and artwork before generating substitutes, then validates source, author, license, slide use, alt text, fit, and focal point in `media-manifest.json`.
- **Production profiles** — `fast`, `balanced`, and `premium` budgets control AI-image count, sourced-image targets, and visual QA depth without weakening content checks.
- **Crop-safe cover media** — transparent heroes float automatically; `contain` preserves complete artwork by default, while explicit `cover` plus a focal point enables intentional photographic crops.
- **Adaptive Brief Gate** — inventories what the user already supplied, asks one compact six-field form only when needed, and avoids redundant questions.
- **Reusable design brief** — captures intent, audience, content ownership, visual preferences, and constraints in a validated `brief.json` before storyboarding.
- **Conditional Source Gate** — when full or partial copy is supplied, accepts attachments, local paths, pasted text, and mixed text/image input while recording source priority, image use, editing level, protected wording, and content gaps.
- **Traceable AI additions** — `source-manifest.json` and `content-map.md` distinguish user copy, references, and AI-authored additions.
- **Stable Deck Protocol v2** — permanent `deck_id` and unique `slide_id` values anchor pages, notes, and revisions, with a stdlib validator, machine-readable JSON Schema, and deterministic legacy migration.
- **Recoverable production pipeline** — one run emits storyboard, visual-plan, HTML, QA, and task-state artifacts; failures identify the exact stage so the same or another AI can resume after correction.
- **Content Director** — produces per-slide narrative, notes, copy, and information-visual diagnoses while limiting automatic edits to safe structural metadata.
- **Unified Agent CLI** — Codex, WorkBuddy, Claude, Gemini, Cursor, automation, and future MCP clients call one stable command with a machine-readable JSON envelope and explicit exit codes.
- **Local MCP tool server** — MCP-capable agents discover six `slides_*` tools plus schemas and instructions as read-only resources, while all file access stays inside an explicit workspace boundary.
- **Secure HTTP API** — web tools, automation platforms, and remote agents call the same production core through bearer authentication, loopback-only defaults, and an OpenAPI 3.1 description.
- **Local production console** — select an outline, validate, build, run the recoverable pipeline, inspect errors and warnings, and preview the result without writing commands.

## Quick start

**Path B — one-click build (reproducible):**
```bash
python scripts/slides.py --json validate brief.json
# When user material is supplied:
python scripts/slides.py --json validate source-manifest.json
python scripts/slides.py --json validate my-talk.json
python scripts/slides.py --json run --outline my-talk.json --out dist/my-talk.html
```
Standard-library only; no network needed (except AI imagery). Output is a single self-contained HTML file.

MCP-capable clients can launch `python scripts/mcp_server.py --workspace <project-directory>`.
See [`references/mcp-server.md`](references/mcp-server.md) for configuration and security boundaries.

Web and automation clients can launch `python scripts/api_server.py --workspace <project-directory>`.
Open `http://127.0.0.1:8765`, then paste the generated bearer token once to use the production console. See [`references/http-api.md`](references/http-api.md) for endpoints and deployment safety, and [`references/production-console.md`](references/production-console.md) for the visual workflow.

**Path A — hand-write:** start from `assets/template.html` or `templates/deck.html`, clone `<section class="slide">` blocks, fill real HTML. See `SKILL.md` for the full workflow.

## AI platform adapters

| Environment | Entry file |
|---|---|
| WorkBuddy / skill-compatible agents | `SKILL.md` |
| OpenAI Codex | `AGENTS.md` |
| Claude Code | `CLAUDE.md` |
| Gemini CLI | `GEMINI.md` |
| Cursor | `.cursor/rules/liquid-glass-slides.mdc` |
| Other agents | `references/INSTRUCTIONS.md` |

## License

[MIT](LICENSE) © 2026 lll192
