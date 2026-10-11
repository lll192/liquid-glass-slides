const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const ui = {
  gate: $('#auth-gate'), form: $('#auth-form'), token: $('#token'), authError: $('#auth-error'),
  outline: $('#outline'), output: $('#output'), brief: $('#brief'), source: $('#source'),
  media: $('#media'), mediaPlan: $('#media-plan'), mediaOutput: $('#media-output'),
  preview: $('#preview'), empty: $('#empty-state'), open: $('#open-preview'), previewTitle: $('#preview-title'),
  statusDot: $('#status-dot'), statusTitle: $('#status-title'), statusMessage: $('#status-message'),
  errors: $('#errors'), warnings: $('#warnings'), raw: $('#raw'),
  outlineCount: $('#metric-outlines'), deckCount: $('#metric-decks'), time: $('#metric-time'),
  projectName: $('#project-name'), projectMeta: $('#project-meta'),
  slideMetric: $('#metric-slides'), visualMetric: $('#metric-visual'), notesMetric: $('#metric-notes'), mediaMetric: $('#metric-media'),
  storyGrid: $('#story-grid'), visualGrid: $('#visual-grid'), visualSummary: $('#visual-summary'),
  assetGrid: $('#asset-grid'), mediaStatus: $('#media-review-status'), approveMedia: $('#approve-media'),
  addMediaForm: $('#add-media-form'), addMediaQuery: $('#add-media-query'),
  addMediaSlide: $('#add-media-slide'), addMediaRole: $('#add-media-role'),
};

let inventory = { files: [], decks: [] };
let project = null;
let running = false;

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
  } catch (error) {
    if (error.status === 401) ui.gate.classList.remove('hidden');
    throw error;
  }
}

function suggestOutput() {
  if (!ui.outline.value) return;
  const stem = ui.outline.value.split('/').pop().replace(/\.json$/i, '').replace(/-outline$/i, '');
  ui.output.value = `dist/${stem || 'deck'}.html`;
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
}

function text(tag, className, value) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  node.textContent = value || '';
  return node;
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
    ui.assetGrid.textContent = '尚未找到媒体。先运行“搜索真实图片”，或由 AI 添加原创视觉。';
    return;
  }
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
    meta.append(titleRow, text('p', '', asset.alt));
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
  if (!selected.length) throw new Error('请至少保留一张图片，再生成成品。');
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
  if (!selected.length) {
    setStatus('error', '至少保留一张图片', '取消不合适的候选后，请至少保留一个素材。');
    return;
  }
  try {
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
    setStatus('success', '图片选择已应用', `当前保留 ${payload.data.assets} 张图片，已更新 ${applied} 个页面。`);
    await loadWorkspace(false);
  } catch (error) {
    setStatus('error', '媒体确认失败', error.message);
  }
}

async function addMedia(event) {
  event.preventDefault();
  if (!project?.media?.manifest) {
    setStatus('error', '还没有图片清单', '请先点击左侧“寻找图片”，再继续添加。');
    return;
  }
  if (!ui.addMediaSlide.value) {
    setStatus('error', '请选择页面', '告诉系统这张图片将用于哪一页。');
    return;
  }
  const submit = ui.addMediaForm.querySelector('button[type="submit"]');
  try {
    submit.disabled = true;
    setStatus('busy', '正在添加图片', '正在根据关键词寻找一张可复用的真实图片。');
    const payload = await api('/v1/add-media', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        manifest: project.media.manifest,
        query: ui.addMediaQuery.value.trim(),
        slideId: ui.addMediaSlide.value,
        role: ui.addMediaRole.value,
      }),
    });
    ui.raw.textContent = JSON.stringify(payload, null, 2);
    ui.addMediaQuery.value = '';
    setStatus('success', '图片已添加', `现在共有 ${payload.data.assets} 张候选图片，可以继续筛选。`);
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
ui.approveMedia.addEventListener('click', approveMedia);
ui.addMediaForm.addEventListener('submit', addMedia);
$('#refresh').addEventListener('click', () => loadWorkspace().catch(() => {}));
$('#logout').addEventListener('click', async () => { await api('/v1/session', { method: 'DELETE' }).catch(() => {}); ui.gate.classList.remove('hidden'); });
document.addEventListener('keydown', (event) => { if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') run('run'); });

const fragment = new URLSearchParams(location.hash.slice(1));
const fragmentToken = fragment.get('token');
if (fragmentToken) authenticateToken(fragmentToken).catch(() => ui.gate.classList.remove('hidden'));
else loadWorkspace().catch(() => {});
