const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const ui = {
  gate: $('#auth-gate'), form: $('#auth-form'), token: $('#token'), authError: $('#auth-error'),
  outline: $('#outline'), output: $('#output'), brief: $('#brief'), source: $('#source'),
  preview: $('#preview'), empty: $('#empty-state'), open: $('#open-preview'), previewTitle: $('#preview-title'),
  statusDot: $('#status-dot'), statusTitle: $('#status-title'), statusMessage: $('#status-message'),
  errors: $('#errors'), warnings: $('#warnings'), raw: $('#raw'),
  outlineCount: $('#metric-outlines'), deckCount: $('#metric-decks'), time: $('#metric-time'),
};

let inventory = { files: [], decks: [] };
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
  select.innerHTML = `<option value="">${emptyLabel}</option>`;
  values.forEach((item) => {
    const option = document.createElement('option');
    option.value = item.path;
    option.textContent = item.path;
    select.append(option);
  });
  if (values.some((item) => item.path === current)) select.value = current;
}

async function loadWorkspace(showReady = true) {
  try {
    const payload = await api('/v1/workspace');
    inventory = payload.data;
    const outlines = inventory.files.filter((file) => file.kind === 'outline');
    fillSelect(ui.outline, outlines, outlines.length ? '选择大纲…' : '未找到 outline.json');
    fillSelect(ui.brief, inventory.files.filter((file) => file.kind === 'brief'), '不使用');
    fillSelect(ui.source, inventory.files.filter((file) => file.kind === 'source-manifest'), '不使用');
    ui.outlineCount.textContent = outlines.length;
    ui.deckCount.textContent = inventory.decks.length;
    if (!ui.outline.value && outlines.length === 1) {
      ui.outline.value = outlines[0].path;
      suggestOutput();
    }
    if (showReady) setStatus('success', '已连接', `工作目录已载入，共发现 ${outlines.length} 份大纲。`);
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

function argumentsFor(action) {
  const outline = ui.outline.value;
  if (!outline) throw new Error('请先选择一份演示大纲。');
  if (action === 'validate') return { path: outline, kind: 'outline' };
  const output = ui.output.value.trim();
  if (!output) throw new Error('请填写输出文件路径。');
  if (action === 'build') return { outline, output };
  return {
    outline, output,
    ...(ui.brief.value ? { brief: ui.brief.value } : {}),
    ...(ui.source.value ? { sourceManifest: ui.source.value } : {}),
  };
}

async function run(action) {
  if (running) return;
  const started = performance.now();
  try {
    const body = argumentsFor(action);
    running = true;
    $$('[data-action]').forEach((button) => button.disabled = true);
    const labels = { validate: '正在验证', build: '正在构建', run: '正在完整生产' };
    setStatus('busy', labels[action], '生产内核正在处理，请保持此页面打开。');
    list(ui.errors, []); list(ui.warnings, []);
    const payload = await api(`/v1/${action}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    });
    ui.raw.textContent = JSON.stringify(payload, null, 2);
    list(ui.errors, payload.errors || []);
    list(ui.warnings, payload.warnings || []);
    setStatus(payload.ok ? 'success' : 'error', payload.ok ? '完成' : '需要处理', payload.message || '操作已结束。');
    if (action !== 'validate' && payload.ok) {
      showPreview(body.output);
      await loadWorkspace(false);
    }
  } catch (error) {
    const payload = error.payload || { errors: [error.message], warnings: [] };
    ui.raw.textContent = JSON.stringify(payload, null, 2);
    list(ui.errors, payload.errors || [error.message]);
    list(ui.warnings, payload.warnings || []);
    setStatus('error', '操作未完成', error.message);
  } finally {
    running = false;
    ui.time.textContent = `${((performance.now() - started) / 1000).toFixed(1)}s`;
    $$('[data-action]').forEach((button) => button.disabled = false);
  }
}

ui.form.addEventListener('submit', async (event) => {
  event.preventDefault();
  ui.authError.textContent = '';
  try {
    await api('/v1/session', { method: 'POST', headers: { Authorization: `Bearer ${ui.token.value}` } });
    ui.token.value = '';
    await loadWorkspace();
  } catch (error) {
    ui.authError.textContent = '连接失败：请确认令牌完整、服务仍在运行。';
  }
});

ui.outline.addEventListener('change', suggestOutput);
$$('[data-action]').forEach((button) => button.addEventListener('click', () => run(button.dataset.action)));
$('#refresh').addEventListener('click', () => loadWorkspace().catch(() => {}));
$('#logout').addEventListener('click', async () => {
  await api('/v1/session', { method: 'DELETE' }).catch(() => {});
  ui.gate.classList.remove('hidden');
});
document.addEventListener('keydown', (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') run('run');
});

loadWorkspace().catch(() => {});
