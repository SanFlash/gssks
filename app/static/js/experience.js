/* Progressive, dependency-free public motion. No content or CMS data is changed. */
(() => {
  'use strict';
  if (!document.querySelector('.site-header')) return;
  const root = document.documentElement;
  const preference = matchMedia('(prefers-reduced-motion: reduce)');
  const fine = matchMedia('(hover: hover) and (pointer: fine)');
  const limited = navigator.connection?.saveData || (navigator.deviceMemory || 8) <= 2 || (navigator.hardwareConcurrency || 8) <= 2;
  let paused = false;
  try { paused = localStorage.getItem('gssks-motion') === 'paused'; } catch {}
  const control = document.createElement('button');
  control.type = 'button'; control.className = 'motion-control';
  document.querySelector('.footer-bottom')?.append(control);
  const progress = document.createElement('div');
  progress.className = 'reading-progress'; progress.setAttribute('aria-hidden', 'true');
  document.body.append(progress);
  let enabled = false;
  const animations = new Set();
  const cards = [...document.querySelectorAll('.focus-card, .project-card, .document-cards article, .recognition-card')];
  function animate(el, frames, options) {
    if (!enabled || !el.animate) return;
    const animation = el.animate(frames, options);
    animations.add(animation);
    animation.onfinish = () => animations.delete(animation);
  }
  const targets = document.querySelectorAll('main section h2, .focus-card, .project-card, .document-cards article, .recognition-card, .founder-feature, .case-study');
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      animate(entry.target, [{opacity: 0, transform: 'translateY(22px)'}, {opacity: 1, transform: 'none'}], {duration: 700, easing: 'cubic-bezier(.2,.7,.2,1)'});
      observer.unobserve(entry.target);
    }), {threshold: .12});
    targets.forEach(el => observer.observe(el));
  }
  cards.forEach(card => {
    card.addEventListener('pointermove', event => {
      if (!enabled || !fine.matches || limited) return;
      const box = card.getBoundingClientRect();
      const x = (event.clientX - box.left) / box.width - .5;
      const y = (event.clientY - box.top) / box.height - .5;
      card.style.transform = `perspective(1000px) rotateX(${-y * 5}deg) rotateY(${x * 5}deg) translateY(-4px)`;
    });
    card.addEventListener('pointerleave', () => card.style.removeProperty('transform'));
    card.addEventListener('focusin', () => card.style.removeProperty('transform'));
  });
  const hero = document.querySelector('.institutional-hero');
  let canvas, ctx, frame = 0, visible = true, width = 0, height = 0, last = 0;
  if (hero && !limited) {
    canvas = document.createElement('canvas');
    canvas.className = 'geometry-canvas'; canvas.setAttribute('aria-hidden', 'true');
    hero.prepend(canvas); ctx = canvas.getContext('2d');
    const resize = () => {
      width = hero.clientWidth; height = hero.clientHeight;
      const dpr = Math.min(devicePixelRatio || 1, 1.5);
      canvas.width = width * dpr; canvas.height = height * dpr;
      ctx?.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    if ('ResizeObserver' in window) new ResizeObserver(resize).observe(hero);
    else window.addEventListener('resize', resize);
    resize();
    if ('IntersectionObserver' in window) new IntersectionObserver(entries => {
      visible = entries[0].isIntersecting; schedule();
    }).observe(hero);
  }
  function draw(now) {
    frame = 0;
    if (!enabled || !visible || document.hidden || !ctx) return;
    if (now - last >= 32) {
      last = now; ctx.clearRect(0, 0, width, height);
      const time = now / 16000, radius = Math.min(width, height) * .39;
      ctx.lineWidth = 1;
      for (let ring = 0; ring < 3; ring++) {
        ctx.strokeStyle = ring === 1 ? 'rgba(181,46,53,.11)' : 'rgba(24,43,120,.10)';
        ctx.beginPath();
        for (let i = 0; i <= 48; i++) {
          const angle = i / 48 * Math.PI * 2;
          const r = radius * (1 + ring * .17) + Math.sin(angle * 6 + time) * 12;
          const x = width * .77 + Math.cos(angle + time * .12) * r;
          const y = height * .5 + Math.sin(angle + time * .12) * r * .8;
          if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        }
        ctx.closePath(); ctx.stroke();
      }
      for (let i = 0; i < (width < 768 ? 12 : 28); i++) {
        const angle = i * 2.399 + time * .15;
        const r = radius * (.5 + (i % 7) / 7);
        ctx.fillStyle = i % 3 ? 'rgba(24,43,120,.20)' : 'rgba(181,46,53,.22)';
        ctx.beginPath(); ctx.arc(width * .77 + Math.cos(angle) * r, height * .5 + Math.sin(angle) * r * .8, 2, 0, Math.PI * 2); ctx.fill();
      }
    }
    schedule();
  }
  function schedule() {
    if (enabled && visible && !document.hidden && ctx && !frame) frame = requestAnimationFrame(draw);
    else if ((!enabled || !visible || document.hidden) && frame) { cancelAnimationFrame(frame); frame = 0; }
  }
  function update() {
    enabled = !paused && !preference.matches;
    root.dataset.motion = enabled ? 'on' : 'off';
    control.textContent = enabled ? 'Pause animations' : 'Animations paused';
    control.setAttribute('aria-pressed', String(!enabled));
    control.disabled = preference.matches;
    control.title = preference.matches ? 'Reduced motion is enabled in your device settings' : 'Toggle decorative animations';
    if (!enabled) {
      animations.forEach(a => a.cancel()); animations.clear();
      cards.forEach(card => card.style.removeProperty('transform'));
      document.querySelectorAll('.reveal').forEach(el => el.classList.add('visible'));
    }
    schedule();
  }
  control.addEventListener('click', () => {
    paused = !paused; try { localStorage.setItem('gssks-motion', paused ? 'paused' : 'on'); } catch {}
    update();
  });
  preference.addEventListener('change', update);
  document.addEventListener('visibilitychange', schedule);
  let scrollFrame = 0;
  function track() {
    scrollFrame = 0;
    const total = root.scrollHeight - innerHeight;
    progress.style.transform = `scaleX(${total > 0 ? scrollY / total : 0})`;
  }
  window.addEventListener('scroll', () => { if (!scrollFrame) scrollFrame = requestAnimationFrame(track); }, {passive: true});
  window.addEventListener('resize', track);
  update(); track();
  document.querySelectorAll('.institutional-hero h1 span').forEach((line, i) => animate(line,
    [{opacity: 0, transform: 'translateY(24px)'}, {opacity: 1, transform: 'none'}],
    {duration: 850, delay: i * 140, easing: 'cubic-bezier(.2,.7,.2,1)', fill: 'backwards'}));
})();
