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

  slides.forEach((s, i) => {
    const d = document.createElement('button');
    d.className = 'dot' + (i === 0 ? ' on' : '');
    d.setAttribute('aria-label', '第 ' + (i+1) + ' 页');
    d.addEventListener('click', () => goTo(i));
    dotsWrap.appendChild(d);
  });
  const dots = Array.from(dotsWrap.children);

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
    if (['ArrowDown','PageDown',' '].includes(e.key)) { e.preventDefault(); goTo(current + 1); }
    else if (['ArrowUp','PageUp'].includes(e.key)) { e.preventDefault(); goTo(current - 1); }
    else if (e.key === 'Home') { e.preventDefault(); goTo(0); }
    else if (e.key === 'End') { e.preventDefault(); goTo(slides.length - 1); }
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
        progress.style.width = ((idx + 1) / slides.length * 100) + '%';
        counter.textContent = String(idx + 1).padStart(2, '0') + ' / ' + String(slides.length).padStart(2, '0');
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
