const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const ui = {
  gate: $('#auth-gate'), form: $('#auth-form'), token: $('#token'), authError: $('#auth-error'),
  outline: $('#outline'), output: $('#output'), brief: $('#brief'), source: $('#source'),
  media: $('#media'), mediaPlan: $('#media-plan'), mediaOutput: $('#media-output'),
  preview: $('#preview'), previewFrame: $('#preview-frame'), empty: $('#empty-state'), open: $('#open-preview'), previewTitle: $('#preview-title'),
  statusDot: $('#status-dot'), statusTitle: $('#status-title'), statusMessage: $('#status-message'),
  errors: $('#errors'), warnings: $('#warnings'), raw: $('#raw'),
  outlineCount: $('#metric-outlines'), deckCount: $('#metric-decks'), time: $('#metric-time'),
  projectName: $('#project-name'), projectMeta: $('#project-meta'),
  slideMetric: $('#metric-slides'), visualMetric: $('#metric-visual'), notesMetric: $('#metric-notes'), mediaMetric: $('#metric-media'),
  storyGrid: $('#story-grid'), visualGrid: $('#visual-grid'), visualSummary: $('#visual-summary'),
  assetGrid: $('#asset-grid'), mediaStatus: $('#media-review-status'), approveMedia: $('#approve-media'),
  uploadMediaForm: $('#upload-media-form'), uploadFiles: $('#upload-media-files'),
  uploadDropzone: $('#upload-dropzone'), addMediaSlide: $('#add-media-slide'),
  addMediaRole: $('#add-media-role'), backgroundOpacity: $('#background-opacity'),
  backgroundOpacityField: $('#background-opacity-field'),
  backgroundOpacityValue: $('#background-opacity-value'),
  aiTask: $('#ai-task'), mcpConfig: $('#mcp-config'), connectionTitle: $('#connection-title'),
  connectionDescription: $('#connection-description'), connectionState: $('#connection-state'),
  installCodex: $('#install-codex'),
};

let inventory = { files: [], decks: [] };
let project = null;
let running = false;
let engineChecked = false;
let integration = null;
let selectedPlatform = 'codex';
const PREVIEW_WIDTH = 1920;
const PREVIEW_HEIGHT = 1080;

function fitPreview() {
  if (!ui.previewFrame || !ui.preview) return;
  const width = ui.previewFrame.clientWidth;
  const height = ui.previewFrame.clientHeight;
  if (!width || !height) return;
  const scale = Math.min(width / PREVIEW_WIDTH, height / PREVIEW_HEIGHT);
  ui.preview.style.setProperty('--preview-scale', String(scale));
}

if ('ResizeObserver' in window) {
  new ResizeObserver(fitPreview).observe(ui.previewFrame);
} else {
  window.addEventListener('resize', fitPreview);
}
ui.preview.addEventListener('load', fitPreview);

function setStatus(kind, title, message) {
  ui.statusDot.className = `status-dot ${kind}`;
  ui.statusTitle.textContent = title;
  ui.statusMessage.textContent = message;
}

function list(target, values) {
  target.innerHTML = '';
  const items = values?.length ? values : ['暂无'];
  items.forEach((value) => {
    const li = document.createElement('li');
    li.textContent = String(value);
    if (!values?.length) li.className = 'muted';
    target.append(li);
  });
}

async function api(path, options = {}) {
  const response = await fetch(path, { credentials: 'same-origin', ...options });
  const payload = await response.json().catch(() => ({ ok: false, errors: ['服务器返回了无法读取的内容'] }));
  if (!response.ok) {
    const error = new Error(payload.message || `请求失败 (${response.status})`);
    error.payload = payload;
    error.status = response.status;
    throw error;
  }
  return payload;
}

async function requireCurrentEngine() {
  if (engineChecked) return;
  const health = await api('/health');
  if (health.search_engine_version !== 'semantic-search-v3') {
    setStatus('error', '服务版本过旧', '请关闭旧命令窗口并重新启动服务；旧版图片搜索已被停用。');
    throw new Error('当前仍连接到旧版图片搜索服务，请重启本地服务后刷新页面');
  }
  engineChecked = true;
}

function fillSelect(select, values, emptyLabel) {
  const current = select.value;
  select.innerHTML = '';
  const empty = document.createElement('option');
  empty.value = '';
  empty.textContent = emptyLabel;
  select.append(empty);
  values.forEach((item) => {
    const option = document.createElement('option');
    option.value = item.path;
    option.textContent = item.path;
    select.append(option);
  });
  if (values.some((item) => item.path === current)) select.value = current;
}

function bestDeck() {
  if (!project) return null;
  const deckId = project.deck.deck_id;
  const candidates = inventory.decks.filter((deck) => deck.name.startsWith(deckId));
  return candidates.sort((a, b) => (b.modified || 0) - (a.modified || 0))[0] || inventory.decks[0] || null;
}

async function loadWorkspace(showReady = true) {
  try {
    await requireCurrentEngine();
    const payload = await api('/v1/workspace');
    inventory = payload.data;
    const outlines = inventory.files.filter((file) => file.kind === 'outline');
    fillSelect(ui.outline, outlines, outlines.length ? '选择演示项目…' : '未找到 outline.json');
    fillSelect(ui.brief, inventory.files.filter((file) => file.kind === 'brief'), '不使用');
    fillSelect(ui.source, inventory.files.filter((file) => file.kind === 'source-manifest'), '不使用');
    fillSelect(ui.media, inventory.files.filter((file) => file.kind === 'media-manifest'), '自动选择');
    fillSelect(ui.mediaPlan, inventory.files.filter((file) => file.kind === 'media-plan'), '未配置');
    const briefs = inventory.files.filter((file) => file.kind === 'brief');
    const plans = inventory.files.filter((file) => file.kind === 'media-plan');
    if (!ui.brief.value && briefs.length === 1) ui.brief.value = briefs[0].path;
    if (!ui.mediaPlan.value && plans.length === 1) ui.mediaPlan.value = plans[0].path;
    ui.outlineCount.textContent = outlines.length;
    ui.deckCount.textContent = inventory.decks.length;
    if (!ui.outline.value && outlines.length === 1) ui.outline.value = outlines[0].path;
    if (ui.outline.value) {
      suggestOutput();
      await loadProject();
    }
    if (showReady) setStatus('success', '已连接', `工作目录已载入，共发现 ${outlines.length} 个演示项目。`);
    ui.gate.classList.add('hidden');
    if (!integration) loadIntegration().catch(() => {
      ui.connectionState.textContent = '等待连接';
    });
  } catch (error) {
    if (error.status === 401) ui.gate.classList.remove('hidden');
    throw error;
  }
}

function suggestOutput() {
  if (!ui.outline.value) return;
  const parts = ui.outline.value.split('/');
  const filename = parts.pop() || 'outline.json';
  const parent = parts.at(-1) || '';
  const stem = filename.replace(/\.json$/i, '').replace(/-outline$/i, '');
  const deckName = stem === 'outline' && parent ? parent : (stem || 'deck');
  ui.output.value = `${parts.length ? `${parts.join('/')}/` : ''}dist/${deckName}.html`;
}

function showPreview(path) {
  if (!path) return;
  const url = `/preview?path=${encodeURIComponent(path)}&v=${Date.now()}`;
  ui.preview.src = url;
  ui.preview.style.display = 'block';
  ui.empty.style.display = 'none';
  ui.open.href = `/preview?path=${encodeURIComponent(path)}`;
  ui.open.classList.remove('disabled');
  ui.previewTitle.textContent = path.split('/').pop();
  requestAnimationFrame(fitPreview);
}

function text(tag, className, value) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  node.textContent = value || '';
  return node;
}

function updateAiTask() {
  if (ui.outline.value) {
    ui.aiTask.value = `请使用 liquid-glass-slides 读取 ${ui.outline.value}，检查并完善逐页内容、视觉方案和演讲者提示，校验通过后生成自包含 HTML 演示。`;
    return;
  }
  ui.aiTask.value = '请先把由 AI 生成的演示项目放入工作目录，然后在左侧选择项目。';
}

function renderConnection() {
  if (!integration) return;
  const labels = {
    codex: ['连接 Codex', '点击下面的按钮安装本地 Skill；重启 Codex 后即可在对话框中直接调用。'],
    claude: ['连接 Claude', '使用 Claude Code 打开当前仓库即可读取 CLAUDE.md；也可以把下方配置加入 MCP 设置。'],
    cursor: ['连接 Cursor', '直接打开仓库即可加载项目规则；需要跨项目调用时可使用下方 MCP 配置。'],
    gemini: ['连接 Gemini', '使用 Gemini CLI 打开仓库即可读取 GEMINI.md；也可以配置本地 MCP。'],
    generic: ['连接其他 AI', '支持 MCP 的客户端复制下方配置；能操作本地文件的 AI 直接打开 GitHub 仓库即可。'],
  };
  [ui.connectionTitle.textContent, ui.connectionDescription.textContent] = labels[selectedPlatform];
  ui.installCodex.hidden = selectedPlatform !== 'codex';
  const config = { mcpServers: { 'liquid-glass-slides': integration.mcp } };
  ui.mcpConfig.value = JSON.stringify(config, null, 2);
  ui.connectionState.textContent = '本地引擎可用';
  updateAiTask();
}

async function loadIntegration() {
  const payload = await api('/v1/integration');
  integration = payload.data;
  renderConnection();
}

async function copyValue(target, button) {
  const value = target.value;
  try {
    await navigator.clipboard.writeText(value);
  } catch (_error) {
    target.focus(); target.select(); document.execCommand('copy');
  }
  const original = button.textContent;
  button.textContent = '已复制';
  setTimeout(() => { button.textContent = original; }, 1400);
}

async function installCodexSkill() {
  try {
    ui.installCodex.disabled = true;
    setStatus('busy', '正在安装 Codex Skill', '正在复制受管文件到本机 Codex Skill 目录。');
    const payload = await api('/v1/install-skill', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target: 'codex' }),
    });
    ui.connectionState.textContent = 'Skill 已安装';
    setStatus('success', '安装完成', payload.data.message);
  } catch (error) {
    setStatus('error', '安装失败', error.message);
  } finally {
    ui.installCodex.disabled = false;
  }
}

async function testEngine() {
  try {
    const payload = await api('/v1/capabilities');
    const count = payload.data?.capabilities?.length || 0;
    ui.connectionState.textContent = '连接正常';
    setStatus('success', '生成引擎正常', count ? `已发现 ${count} 项引擎能力。` : '本地生成内核可以正常调用。');
  } catch (error) {
    ui.connectionState.textContent = '连接失败';
    setStatus('error', '引擎测试失败', error.message);
  }
}

function renderStory() {
  ui.storyGrid.innerHTML = '';
  ui.storyGrid.classList.remove('empty-grid');
  project.slides.forEach((slide) => {
    const card = document.createElement('article');
    card.className = 'story-card';
    const head = document.createElement('div');
    head.className = 'card-head';
    head.append(text('b', 'page-no', String(slide.order).padStart(2, '0')));
    head.append(text('span', 'role-tag', slide.story_role));
    card.append(head, text('h3', '', slide.title), text('p', 'main-point', slide.main_point || '尚未填写核心结论'));
    if (slide.transition) card.append(text('p', 'transition', `→ ${slide.transition}`));
    const editor = document.createElement('details');
    editor.className = 'slide-editor';
    const summary = document.createElement('summary');
    summary.textContent = '编辑这一页';
    editor.append(summary);
    const fields = [
      ['title', '页面标题', slide.title],
      ['main_point', '核心结论', slide.main_point],
      ['transition', '转场提示', slide.transition],
      ['speaker_notes', '演讲者笔记', Array.isArray(slide.speaker_notes) ? slide.speaker_notes.join('\n') : slide.speaker_notes],
    ];
    (slide.content_fields || []).forEach((field) => fields.splice(1, 0, [field.key, field.label, field.value, field]));
    fields.forEach(([key, label, value, contentField]) => {
      const fieldLabel = document.createElement('label');
      fieldLabel.textContent = label;
      const input = contentField?.type === 'html' ? document.createElement('div') : document.createElement('textarea');
      input.dataset.editField = key;
      if (contentField) input.dataset.contentType = contentField.type;
      if (contentField?.columns) input.dataset.columns = JSON.stringify(contentField.columns);
      if (contentField?.type === 'html') {
        input.className = 'editable-rich-text';
        input.contentEditable = 'true';
        input.innerHTML = value || '';
        input.setAttribute('role', 'textbox');
        input.setAttribute('aria-multiline', 'true');
      } else {
        input.value = value || '';
        input.rows = key === 'speaker_notes' ? 5 : (contentField?.type === 'list' ? 5 : 2);
      }
      fieldLabel.append(input);
      if (contentField?.hint) fieldLabel.append(text('small', 'content-field-note', contentField.hint));
      editor.append(fieldLabel);
    });
    const save = document.createElement('button');
    save.type = 'button';
    save.className = 'primary compact';
    save.textContent = '保存本页';
    save.addEventListener('click', () => updateSlide(slide.slide_id, editor));
    editor.append(save);
    card.append(editor);
    ui.storyGrid.append(card);
  });
}

async function updateSlide(slideId, editor) {
  const patch = {};
  editor.querySelectorAll('[data-edit-field]').forEach((input) => {
    const raw = input.dataset.contentType === 'html' ? input.innerHTML.trim() : input.value.trim();
    if (input.dataset.contentType === 'list') {
      const columns = JSON.parse(input.dataset.columns || '[]');
      patch[input.dataset.editField] = raw.split(/\r?\n/).map((line) => line.trim()).filter(Boolean).map((line) => {
        const parts = line.split(/[｜|]/).map((part) => part.trim());
        return Object.fromEntries(columns.map((column, index) => [column, parts[index] || '']));
      });
    } else {
      patch[input.dataset.editField] = raw;
    }
  });
  try {
    setStatus('busy', '正在保存页面', '正在把修改写回演示项目。');
    const payload = await api('/v1/update-slide', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ outline: ui.outline.value, slideId, patch }),
    });
    ui.raw.textContent = JSON.stringify(payload, null, 2);
    setStatus('success', '页面已保存', '点击“更新预览”即可查看修改后的页面。');
    await loadProject();
  } catch (error) {
    setStatus('error', '保存失败', error.message);
  }
}

function renderVisuals() {
  ui.visualGrid.innerHTML = '';
  ui.visualGrid.classList.remove('empty-grid');
  ui.visualSummary.innerHTML = '';
  const score = project.metrics.visual_coverage;
  const ring = document.createElement('div');
  ring.className = 'coverage-ring';
  ring.style.setProperty('--score', `${score * 3.6}deg`);
  ring.append(text('strong', '', `${score}%`), text('span', '', '有效视觉覆盖'));
  ui.visualSummary.append(ring, text('p', '', '图片、图表、表格、流程和关系图才计入信息视觉；纯装饰背景不会虚增分数。'));
  project.slides.forEach((slide) => {
    const row = document.createElement('article');
    row.className = `visual-row ${slide.meaningful_visual ? 'covered' : 'text-only'}`;
    row.append(text('b', 'page-no', String(slide.order).padStart(2, '0')));
    const body = document.createElement('div');
    body.append(text('h3', '', slide.title), text('p', '', slide.visual_purpose || '当前页面以文字节奏承担表达。'));
    row.append(body, text('span', 'visual-tag', slide.visual_type));
    ui.visualGrid.append(row);
  });
}

function renderAssets() {
  ui.assetGrid.innerHTML = '';
  ui.assetGrid.classList.remove('empty-grid');
  const media = project.media;
  const selectedCount = media.assets.filter((asset) => asset.selected !== false).length;
  ui.mediaStatus.textContent = media.manifest
    ? `${selectedCount}/${media.assets.length} 已选 · ${media.reviewed ? '已复核' : '等待复核'}`
    : '尚无媒体清单';
  ui.approveMedia.disabled = !media.manifest || !media.assets.length;
  if (!media.assets.length) {
    ui.assetGrid.classList.add('empty-grid');
    ui.assetGrid.textContent = '尚未添加图片。可以把本地图片拖到上方上传区域。';
    return;
  }
  const roleLabels = { background: '背景图', content: '内容图', decorative: '已停用', hero: '主视觉', reference: '参考图' };
  const slideLabels = new Map(project.slides.map((slide) => [slide.slide_id, `${String(slide.order).padStart(2, '0')} · ${slide.title}`]));
  media.assets.forEach((asset) => {
    const card = document.createElement('article');
    card.className = 'asset-card';
    if (asset.asset_path) {
      const img = document.createElement('img');
      img.src = `/asset?path=${encodeURIComponent(asset.asset_path)}`;
      img.alt = asset.alt || '';
      img.loading = 'lazy';
      card.append(img);
    }
    const meta = document.createElement('div');
    const titleRow = document.createElement('div');
    titleRow.className = 'asset-title';
    const choice = document.createElement('input');
    choice.type = 'checkbox';
    choice.checked = asset.selected !== false;
    choice.dataset.assetId = asset.asset_id;
    choice.setAttribute('aria-label', `保留 ${asset.asset_id}`);
    choice.addEventListener('change', () => card.classList.toggle('excluded', !choice.checked));
    card.classList.toggle('excluded', !choice.checked);
    titleRow.append(choice);
    titleRow.append(text('strong', '', asset.asset_id), text('span', `origin ${asset.origin}`, asset.origin));
    const locations = (asset.slide_ids || []).map((id) => slideLabels.get(id) || id).join('、') || '未指定页面';
    const info = document.createElement('dl');
    info.className = 'asset-info';
    info.append(
      text('dt', '', '出现页面'), text('dd', '', locations),
      text('dt', '', '图片类型'), text('dd', '', roleLabels[asset.role] || asset.role || '内容图'),
      text('dt', '', '显示方式'), text('dd', '', asset.role === 'background' ? '全屏铺展' : '自动排版'),
    );
    meta.append(titleRow, info, text('p', '', asset.alt));
    if (asset.role === 'background') {
      const opacityRow = document.createElement('label');
      opacityRow.className = 'asset-opacity';
      const opacity = Math.round(Number(asset.opacity ?? .55) * 100);
      const value = text('output', '', `${opacity}%`);
      const slider = document.createElement('input');
      slider.type = 'range'; slider.min = '0'; slider.max = '100'; slider.value = String(opacity);
      slider.style.setProperty('--range-fill', `${opacity}%`);
      slider.addEventListener('input', () => {
        value.textContent = `${slider.value}%`;
        slider.style.setProperty('--range-fill', `${slider.value}%`);
      });
      slider.addEventListener('change', async () => {
        try {
          await api('/v1/update-media', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              manifest: project.media.manifest, outline: ui.outline.value,
              assetId: asset.asset_id, opacity: Number(slider.value) / 100,
            }),
          });
          asset.opacity = Number(slider.value) / 100;
          if (ui.output.value) {
            await api('/v1/build', {
              method: 'POST', headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ outline: ui.outline.value, output: ui.output.value }),
            });
            showPreview(ui.output.value);
          }
          setStatus('success', '不透明度已生效', '背景不透明度已经同步到当前页面和预览。');
        } catch (error) { setStatus('error', '不透明度保存失败', error.message); }
      });
      opacityRow.append(text('span', '', '背景不透明度'), value, slider);
      meta.append(opacityRow);
    }
    const credit = asset.origin === 'web' ? `${asset.author || '未知作者'} · ${asset.license || '许可待确认'}` : (asset.notes || '项目原创素材');
    meta.append(text('small', '', credit));
    card.append(meta);
    ui.assetGrid.append(card);
  });
}

async function loadProject() {
  if (!ui.outline.value) return;
  const mediaQuery = ui.media.value ? `&mediaManifest=${encodeURIComponent(ui.media.value)}` : '';
  const payload = await api(`/v1/project?outline=${encodeURIComponent(ui.outline.value)}${mediaQuery}`);
  project = payload.data;
  ui.projectName.textContent = project.deck.title;
  ui.projectMeta.textContent = `${project.deck.slides} 页 · ${project.deck.deck_id}`;
  ui.slideMetric.textContent = project.deck.slides;
  ui.visualMetric.textContent = `${project.metrics.visual_coverage}%`;
  ui.notesMetric.textContent = `${project.metrics.speaker_notes_coverage}%`;
  ui.mediaMetric.textContent = `${project.metrics.web_assets} / ${project.metrics.ai_assets}`;
  ui.addMediaSlide.innerHTML = '<option value="">选择页面</option>';
  project.slides.forEach((slide) => {
    const option = document.createElement('option');
    option.value = slide.slide_id;
    option.textContent = `${String(slide.order).padStart(2, '0')} · ${slide.title}`;
    ui.addMediaSlide.append(option);
  });
  renderStory(); renderVisuals(); renderAssets();
  updateAiTask();
  if (project.media.manifest && [...ui.media.options].some((option) => option.value === project.media.manifest)) {
    ui.media.value = project.media.manifest;
  }
  const deck = bestDeck();
  if (deck) { ui.output.value = deck.path; showPreview(deck.path); }
}

function argumentsFor(action) {
  if (action === 'source-images') {
    if (!ui.mediaPlan.value) throw new Error('请先选择网络图片计划。');
    if (!ui.mediaOutput.value.trim()) throw new Error('请填写候选清单输出路径。');
    return { plan: ui.mediaPlan.value, projectDir: '.', manifest: ui.mediaOutput.value.trim(), workers: 4 };
  }
  const outline = ui.outline.value;
  if (!outline) throw new Error('请先选择一个演示项目。');
  if (action === 'validate') return { path: outline, kind: 'outline' };
  const output = ui.output.value.trim();
  if (!output) throw new Error('请填写输出文件路径。');
  if (action === 'build') return { outline, output };
  return {
    outline, output,
    ...(ui.brief.value ? { brief: ui.brief.value } : {}),
    ...(ui.source.value ? { sourceManifest: ui.source.value } : {}),
    ...(ui.media.value ? { mediaManifest: ui.media.value } : {}),
  };
}

async function run(action) {
  if (running) return;
  const started = performance.now();
  try {
    if (action === 'run' || action === 'build') await applyMediaSelection();
    const body = argumentsFor(action);
    running = true;
    $$('[data-action]').forEach((button) => button.disabled = true);
    const labels = { validate: '正在检查', build: '正在更新预览', run: '正在生成成品', 'source-images': '正在寻找图片' };
    setStatus('busy', labels[action], action === 'source-images' ? '正在寻找并下载可以复用的真实图片。' : '正在处理，请保持页面打开。');
    list(ui.errors, []); list(ui.warnings, []);
    const payload = await api(`/v1/${action}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    ui.raw.textContent = JSON.stringify(payload, null, 2);
    list(ui.errors, payload.errors || []); list(ui.warnings, payload.warnings || []);
    setStatus(payload.ok ? 'success' : 'error', payload.ok ? '完成' : '需要处理', payload.message || '操作已结束。');
    if (action !== 'validate' && payload.ok) {
      await loadWorkspace(false);
      if (action === 'build' || action === 'run') showPreview(body.output);
      if (action === 'source-images') {
        if ([...ui.media.options].some((option) => option.value === body.manifest)) ui.media.value = body.manifest;
        await loadProject();
        switchView('assets');
      }
    }
  } catch (error) {
    const payload = error.payload || { errors: [error.message], warnings: [] };
    ui.raw.textContent = JSON.stringify(payload, null, 2);
    list(ui.errors, payload.errors || [error.message]); list(ui.warnings, payload.warnings || []);
    setStatus('error', '操作未完成', error.message);
  } finally {
    running = false;
    ui.time.textContent = `${((performance.now() - started) / 1000).toFixed(1)}s`;
    $$('[data-action]').forEach((button) => button.disabled = false);
  }
}

async function applyMediaSelection() {
  if (!project?.media?.manifest) return;
  const checkboxes = $$('[data-asset-id]');
  const selected = checkboxes.length
    ? checkboxes.filter((input) => input.checked).map((input) => input.dataset.assetId)
    : project.media.assets.map((asset) => asset.asset_id);
  setStatus('busy', '正在保存图片选择', '生成前先确认当前保留的图片。');
  await api('/v1/review-media', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      manifest: project.media.manifest,
      outline: ui.outline.value,
      selectedAssetIds: selected,
    }),
  });
  project.media.reviewed = true;
}

function switchView(view) {
  $$('[data-view]').forEach((button) => button.classList.toggle('active', button.dataset.view === view));
  $$('[data-panel]').forEach((panel) => panel.classList.toggle('active', panel.dataset.panel === view));
}

async function approveMedia() {
  if (!project?.media?.manifest) return;
  const selected = $$('[data-asset-id]:checked').map((input) => input.dataset.assetId);
  const output = ui.output.value.trim();
  try {
    ui.approveMedia.disabled = true;
    setStatus('busy', '正在应用图片选择', '正在清理页面图片、重新生成并刷新预览。');
    const payload = await api('/v1/review-media', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        manifest: project.media.manifest,
        outline: ui.outline.value,
        selectedAssetIds: selected,
      }),
    });
    ui.raw.textContent = JSON.stringify(payload, null, 2);
    const applied = payload.data.applied_slides?.length || 0;
    if (output) {
      await api('/v1/build', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ outline: ui.outline.value, output }),
      });
    }
    await loadWorkspace(false);
    if (output) showPreview(output);
    setStatus('success', '图片选择已应用', `当前保留 ${payload.data.assets} 张图片，已更新 ${applied} 个页面，预览已经刷新。`);
  } catch (error) {
    setStatus('error', '媒体确认失败', error.message);
  } finally {
    ui.approveMedia.disabled = false;
  }
}

function fileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error(`无法读取 ${file.name}`));
    reader.readAsDataURL(file);
  });
}

async function uploadMedia(event) {
  event.preventDefault();
  if (!project?.media?.manifest) {
    setStatus('error', '还没有图片清单', '请先为当前项目建立媒体清单。');
    return;
  }
  if (!ui.addMediaSlide.value) {
    setStatus('error', '请选择页面', '告诉系统这张图片将用于哪一页。');
    return;
  }
  const files = [...ui.uploadFiles.files];
  if (!files.length) {
    setStatus('error', '请选择图片', '点击上传区域，或者把图片拖进来。');
    return;
  }
  if (ui.addMediaRole.value === 'background' && files.length > 1) {
    setStatus('error', '背景图只能上传一张', '内容图可以一次上传多张。');
    return;
  }
  if (ui.addMediaRole.value === 'content' && files.length > 3) {
    setStatus('error', '内容图最多三张', '请一次选择不超过三张内容图。');
    return;
  }
  const submit = ui.uploadMediaForm.querySelector('button[type="submit"]');
  try {
    submit.disabled = true;
    setStatus('busy', '正在上传图片', `正在处理 ${files.length} 张本地图片。`);
    let payload = null;
    for (const file of files) {
      if (file.size > 15 * 1024 * 1024) throw new Error(`${file.name} 超过 15 MB`);
      payload = await api('/v1/upload-media', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          manifest: project.media.manifest, filename: file.name,
          data: await fileAsDataUrl(file), slideId: ui.addMediaSlide.value,
          role: ui.addMediaRole.value, opacity: Number(ui.backgroundOpacity.value) / 100,
        }),
      });
    }
    ui.raw.textContent = JSON.stringify(payload, null, 2);
    ui.uploadMediaForm.reset();
    ui.backgroundOpacity.value = '55'; ui.backgroundOpacityValue.textContent = '55%';
    ui.backgroundOpacityField.hidden = true; ui.uploadFiles.multiple = true;
    ui.uploadDropzone.querySelector('strong').textContent = '拖拽图片到这里';
    setStatus('success', '本地图片已添加', `已上传 ${files.length} 张；保存后将自动选择合适排版。`);
    await loadWorkspace(false);
    switchView('assets');
  } catch (error) {
    setStatus('error', '添加失败', error.message);
  } finally {
    submit.disabled = false;
  }
}

async function authenticateToken(token) {
  await api('/v1/session', { method: 'POST', headers: { Authorization: `Bearer ${token}` } });
  history.replaceState(null, '', location.pathname + location.search);
  await loadWorkspace();
}

ui.form.addEventListener('submit', async (event) => {
  event.preventDefault(); ui.authError.textContent = '';
  try { await authenticateToken(ui.token.value); ui.token.value = ''; }
  catch (error) { ui.authError.textContent = '连接失败：请确认令牌完整、服务仍在运行。'; }
});
ui.outline.addEventListener('change', async () => { suggestOutput(); await loadProject().catch((error) => setStatus('error', '读取项目失败', error.message)); });
ui.media.addEventListener('change', () => loadProject().catch((error) => setStatus('error', '读取媒体失败', error.message)));
$$('[data-action]').forEach((button) => button.addEventListener('click', () => run(button.dataset.action)));
$$('[data-view]').forEach((button) => button.addEventListener('click', () => switchView(button.dataset.view)));
$$('[data-platform]').forEach((button) => button.addEventListener('click', () => {
  selectedPlatform = button.dataset.platform;
  $$('[data-platform]').forEach((item) => item.classList.toggle('active', item === button));
  renderConnection();
}));
ui.installCodex.addEventListener('click', installCodexSkill);
$('#test-engine').addEventListener('click', testEngine);
$('#copy-ai-task').addEventListener('click', (event) => copyValue(ui.aiTask, event.currentTarget));
$('#copy-mcp-config').addEventListener('click', (event) => copyValue(ui.mcpConfig, event.currentTarget));
ui.approveMedia.addEventListener('click', approveMedia);
ui.uploadMediaForm.addEventListener('submit', uploadMedia);
ui.addMediaRole.addEventListener('change', () => {
  const background = ui.addMediaRole.value === 'background';
  ui.backgroundOpacityField.hidden = !background;
  ui.uploadFiles.multiple = !background;
});
ui.backgroundOpacity.style.setProperty('--range-fill', `${ui.backgroundOpacity.value}%`);
ui.backgroundOpacity.addEventListener('input', () => {
  ui.backgroundOpacityValue.textContent = `${ui.backgroundOpacity.value}%`;
  ui.backgroundOpacity.style.setProperty('--range-fill', `${ui.backgroundOpacity.value}%`);
});
['dragenter', 'dragover'].forEach((name) => ui.uploadDropzone.addEventListener(name, (event) => {
  event.preventDefault(); ui.uploadDropzone.classList.add('dragging');
}));
['dragleave', 'drop'].forEach((name) => ui.uploadDropzone.addEventListener(name, (event) => {
  event.preventDefault(); ui.uploadDropzone.classList.remove('dragging');
}));
ui.uploadDropzone.addEventListener('drop', (event) => {
  const files = [...event.dataTransfer.files].filter((file) => file.type.startsWith('image/'));
  if (ui.addMediaRole.value === 'background' && files.length > 1) files.splice(1);
  const transfer = new DataTransfer(); files.forEach((file) => transfer.items.add(file));
  ui.uploadFiles.files = transfer.files;
  ui.uploadDropzone.querySelector('strong').textContent = files.length ? `已选择 ${files.length} 张图片` : '拖拽图片到这里';
});
ui.uploadFiles.addEventListener('change', () => {
  ui.uploadDropzone.querySelector('strong').textContent = ui.uploadFiles.files.length ? `已选择 ${ui.uploadFiles.files.length} 张图片` : '拖拽图片到这里';
});
$('#refresh').addEventListener('click', () => loadWorkspace().catch(() => {}));
$('#logout').addEventListener('click', async () => { await api('/v1/session', { method: 'DELETE' }).catch(() => {}); ui.gate.classList.remove('hidden'); });
document.addEventListener('keydown', (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') run('run');
});

const fragment = new URLSearchParams(location.hash.slice(1));
const fragmentToken = fragment.get('token');
if (fragmentToken) authenticateToken(fragmentToken).catch(() => ui.gate.classList.remove('hidden'));
else loadWorkspace().catch(() => {});
