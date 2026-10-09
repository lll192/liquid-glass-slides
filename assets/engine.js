/* ============================================================
   liquid-glass-slides · ENGINE JS (extracted from template.html)
   Consumed by scripts/build.py and inlined into the final deck.
   ============================================================ */
(function(){
  const deck = document.querySelector('.deck');
  const slides = Array.from(deck.querySelectorAll('.slide'));
  const dotsWrap = document.querySelector('.dots');
  const progress = document.querySelector('.progress');
  const counter = document.querySelector('.counter');
  let current = 0, wheelLock = false;
  let notesVisible = new URLSearchParams(location.search).has('notes');
  const isChinese = (document.documentElement.lang || '').toLowerCase().startsWith('zh');
  const sessionNotes = new Map();
  const deckNoteKey = 'liquid-glass-notes:' + location.pathname + ':' + document.title + ':';

  const notesPanel = document.createElement('aside');
  notesPanel.className = 'presenter-notes';
  notesPanel.setAttribute('aria-live', 'polite');
  notesPanel.innerHTML = '<div class="presenter-notes-head"><span>Narrative Director</span><button type="button" aria-label="Close presenter cues">×</button></div>' +
    '<div class="presenter-notes-body"><div class="presenter-cues"></div>' +
    '<div class="presenter-editor"><label for="presenter-notes-editor">' + (isChinese ? '演讲者笔记' : 'Speaker notes') + '</label>' +
    '<textarea id="presenter-notes-editor" class="presenter-notes-editor" spellcheck="true"></textarea>' +
    '<p class="presenter-notes-status" aria-live="polite"></p></div></div>';
  document.body.appendChild(notesPanel);
  notesPanel.querySelector('button').addEventListener('click', () => setNotesVisible(false));
  notesPanel.id = 'presenter-notes';
  const notesEditor = notesPanel.querySelector('.presenter-notes-editor');
  const notesStatus = notesPanel.querySelector('.presenter-notes-status');

  function noteStorageKey(){ return deckNoteKey + String(current + 1); }
  function sourceNoteText(){
    const source = slides[current] && slides[current].querySelector('.speaker-notes');
    if (!source) return '';
    return Array.from(source.querySelectorAll('p')).map((p) => p.textContent.trim()).filter(Boolean).join('\n\n') || source.textContent.trim();
  }
  function readNote(){
    const key = noteStorageKey();
    try {
      const saved = localStorage.getItem(key);
      if (saved !== null) return saved;
    } catch (error) {}
    return sessionNotes.has(key) ? sessionNotes.get(key) : sourceNoteText();
  }
  function saveNote(){
    const key = noteStorageKey();
    const value = notesEditor.value;
    sessionNotes.set(key, value);
    let persisted = false;
    try { localStorage.setItem(key, value); persisted = true; } catch (error) {}
    notesStatus.textContent = persisted
      ? (isChinese ? '已自动保存到本机浏览器' : 'Saved locally in this browser')
      : (isChinese ? '已保存在本次会话' : 'Saved for this session');
  }
  notesEditor.addEventListener('input', saveNote);

  function updateSpeakerNotes(){
    const cues = slides[current] && slides[current].querySelector('.narrative-cues');
    const cueBox = notesPanel.querySelector('.presenter-cues');
    cueBox.innerHTML = cues && cues.innerHTML ? cues.innerHTML : '';
    cueBox.hidden = !cueBox.innerHTML;
    notesEditor.value = readNote();
    notesEditor.placeholder = isChinese ? '在这里直接补充或修改本页讲稿……' : 'Add or edit notes for this slide…';
    notesStatus.textContent = isChinese ? '输入内容会自动保存' : 'Changes are saved automatically';
    notesPanel.dataset.slide = String(current + 1);
    notesPanel.dataset.role = slides[current] ? (slides[current].dataset.storyRole || '') : '';
  }
  function setNotesVisible(value){
    notesVisible = Boolean(value);
    document.body.classList.toggle('notes-visible', notesVisible);
    notesPanel.setAttribute('aria-hidden', notesVisible ? 'false' : 'true');
    if (notesVisible) updateSpeakerNotes();
    updateProgress();
  }
  setNotesVisible(notesVisible);

  /* Lightweight runtime QA: inspect real browser geometry without screenshots. */
  function runQualityAudit(){
    const issues = [];
    slides.forEach((slide, index) => {
      const page = index + 1;
      const pageIssues = [];
      // Audit the readable content box, not the full slide. Decorative ripple
      // scaling and reveal transforms intentionally extend beyond the viewport.
      const contentBox = slide.querySelector('.slide-content') || slide;
      const overflowX = contentBox.scrollWidth > contentBox.clientWidth + 2;
      const overflowY = contentBox.scrollHeight > contentBox.clientHeight + 2;
      if (overflowX) pageIssues.push({ code:'horizontal-overflow', severity:'error', message:'content exceeds slide width' });
      if (overflowY) pageIssues.push({ code:'vertical-overflow', severity:'error', message:'content exceeds slide height' });

      const title = slide.querySelector('h1, h2');
      if (title) {
        const style = getComputedStyle(title);
        const lineHeight = parseFloat(style.lineHeight) || parseFloat(style.fontSize) * 1.15;
        const lines = Math.max(1, Math.round(title.getBoundingClientRect().height / lineHeight));
        const limit = title.tagName === 'H1' ? 3 : 2;
        if (lines > limit) pageIssues.push({
          code:'title-wrap', severity:'warning',
          message:'title occupies ' + lines + ' lines; shorten or widen the title field'
        });
      }

      slide.querySelectorAll('p:not(.footnote), li').forEach((el) => {
        if (!el.textContent.trim() || el.offsetParent === null) return;
        const size = parseFloat(getComputedStyle(el).fontSize);
        if (size && size < 14) pageIssues.push({
          code:'small-type', severity:'warning', message:'readable text falls below 14px'
        });
      });
      slide.querySelectorAll('figcaption, .footnote').forEach((el) => {
        if (!el.textContent.trim() || el.offsetParent === null) return;
        const size = parseFloat(getComputedStyle(el).fontSize);
        if (size && size < 11.5) pageIssues.push({
          code:'small-caption', severity:'warning', message:'caption text falls below 11.5px'
        });
      });

      const shell = slide.querySelector('.composition-shell, .wrap');
      if (shell) {
        const sr = slide.getBoundingClientRect();
        const cr = shell.getBoundingClientRect();
        if (cr.left < sr.left - 2 || cr.right > sr.right + 2 || cr.top < sr.top - 2 || cr.bottom > sr.bottom + 2) {
          pageIssues.push({ code:'out-of-bounds', severity:'error', message:'main composition crosses the slide boundary' });
        }
      }

      const unique = [];
      pageIssues.forEach((issue) => {
        if (!unique.some((seen) => seen.code === issue.code)) unique.push(issue);
      });
      slide.dataset.qa = unique.some((i) => i.severity === 'error') ? 'error' : (unique.length ? 'warning' : 'pass');
      unique.forEach((issue) => issues.push(Object.assign({ slide:page, layout:slide.dataset.layout || '' }, issue)));
    });
    const report = { viewport:{ width:innerWidth, height:innerHeight }, checkedAt:new Date().toISOString(), issues:issues };
    window.__LG_BUILD_REPORT__ = window.__LG_BUILD_REPORT__ || {};
    window.__LG_BUILD_REPORT__.runtime = report;
    if (issues.length) console.warn('[Liquid Glass QA]', issues);
    if (new URLSearchParams(location.search).has('qa')) {
      document.body.classList.add('qa-visible');
      let badge = document.querySelector('.qa-status');
      if (!badge) {
        badge = document.createElement('button');
        badge.className = 'qa-status';
        badge.addEventListener('click', () => console.table(runQualityAudit().issues));
        document.body.appendChild(badge);
      }
      const errors = issues.filter((issue) => issue.severity === 'error').length;
      badge.textContent = errors ? 'QA · ' + errors + ' errors' : (issues.length ? 'QA · ' + issues.length + ' warnings' : 'QA · pass');
      badge.dataset.state = errors ? 'error' : (issues.length ? 'warning' : 'pass');
      badge.title = 'Click to print the current viewport report in the console';
    }
    return report;
  }
  window.LiquidGlassQA = { run:runQualityAudit, get report(){ return (window.__LG_BUILD_REPORT__ || {}).runtime || null; } };

  function scheduleQualityAudit(){
    requestAnimationFrame(() => requestAnimationFrame(runQualityAudit));
  }
  const automaticQA = !window.__LG_BUILD_REPORT__ || window.__LG_BUILD_REPORT__.qualityIntelligence !== false;
  if (automaticQA && document.fonts && document.fonts.ready) document.fonts.ready.then(scheduleQualityAudit);
  else if (automaticQA) window.addEventListener('load', scheduleQualityAudit, { once:true });
  let qaResizeTimer = null;
  window.addEventListener('resize', () => {
    clearTimeout(qaResizeTimer);
    if (automaticQA) qaResizeTimer = setTimeout(scheduleQualityAudit, 180);
  });

  slides.forEach((s, i) => {
    const d = document.createElement('button');
    d.className = 'dot' + (i === 0 ? ' on' : '');
    d.setAttribute('aria-label', '第 ' + (i+1) + ' 页');
    d.addEventListener('click', () => goTo(i));
    dotsWrap.appendChild(d);
  });
  const dots = Array.from(dotsWrap.children);

  function updateProgress(){
    const fraction = (current + 1) / slides.length;
    progress.style.width = notesVisible
      ? 'calc((100vw - var(--presenter-rail)) * ' + fraction + ')'
      : (fraction * 100) + '%';
  }

  function goTo(i){
    i = Math.max(0, Math.min(slides.length - 1, i));
    slides[i].scrollIntoView({ behavior: 'smooth' });
  }

  deck.addEventListener('wheel', (e) => {
    e.preventDefault();
    if (wheelLock || Math.abs(e.deltaY) < 8) return;
    wheelLock = true;
    goTo(current + (e.deltaY > 0 ? 1 : -1));
    setTimeout(() => wheelLock = false, 750);
  }, { passive: false });

  window.addEventListener('keydown', (e) => {
    if ((e.target && /input|textarea|select/i.test(e.target.tagName))) return;
    if (['ArrowDown','PageDown',' '].includes(e.key)) { e.preventDefault(); goTo(current + 1); }
    else if (['ArrowUp','PageUp'].includes(e.key)) { e.preventDefault(); goTo(current - 1); }
    else if (e.key === 'Home') { e.preventDefault(); goTo(0); }
    else if (e.key === 'End') { e.preventDefault(); goTo(slides.length - 1); }
    else if (e.key.toLowerCase() === 'n') { e.preventDefault(); setNotesVisible(!notesVisible); }
  });

  let touchY = null;
  deck.addEventListener('touchstart', (e) => { touchY = e.touches[0].clientY; }, { passive: true });
  deck.addEventListener('touchmove', (e) => {
    if (touchY === null) return;
    const dy = touchY - e.touches[0].clientY;
    if (Math.abs(dy) > 42) { goTo(current + (dy > 0 ? 1 : -1)); touchY = null; }
  }, { passive: true });

  const io = new IntersectionObserver((entries) => {
    entries.forEach((en) => {
      if (en.isIntersecting && en.intersectionRatio >= 0.55) {
        const idx = slides.indexOf(en.target);
        current = idx;
        slides.forEach((s) => s.classList.remove('active'));
        en.target.classList.add('active');
        dots.forEach((d, i) => d.classList.toggle('on', i === idx));
        updateProgress();
        counter.textContent = String(idx + 1).padStart(2, '0') + ' / ' + String(slides.length).padStart(2, '0');
        if (notesVisible) updateSpeakerNotes();
      }
    });
  }, { root: deck, threshold: [0.55] });

  slides.forEach((s) => io.observe(s));
  slides[0].classList.add('active');

  /* 鼠标视差 */
  const px = document.querySelectorAll('.bg .blob, .glyphs span, .orb');
  let raf = null;
  window.addEventListener('mousemove', (e) => {
    if (raf) return;
    raf = requestAnimationFrame(() => {
      const dx = (e.clientX / window.innerWidth - .5);
      const dy = (e.clientY / window.innerHeight - .5);
      px.forEach((el, i) => {
        const depth = (i % 3 + 1) * 6;
        el.style.marginLeft = (dx * depth) + 'px';
        el.style.marginTop = (dy * depth) + 'px';
      });
      raf = null;
    });
  });

  /* 3D 悬浮倾斜 */
  if (window.matchMedia('(hover:hover)').matches && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    document.querySelectorAll('.tilt').forEach((card) => {
      card.addEventListener('mousemove', (e) => {
        const r = card.getBoundingClientRect();
        const rx = ((e.clientY - r.top) / r.height - .5) * -6;
        const ry = ((e.clientX - r.left) / r.width - .5) * 6;
        card.style.transform = 'perspective(800px) rotateX(' + rx + 'deg) rotateY(' + ry + 'deg) translateY(-3px)';
      });
      card.addEventListener('mouseleave', () => { card.style.transform = ''; });
    });
  }
})();
