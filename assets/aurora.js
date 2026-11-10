(function () {
  'use strict';
  var canvas = document.querySelector('.aurora');
  if (!canvas) return;
  var ctx = canvas.getContext('2d', { alpha: true });
  if (!ctx) return;
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)');
  var fine = window.matchMedia('(hover: hover) and (pointer: fine)');
  var hero = canvas.closest('.hero');
  var w = 0, h = 0, dpr = 1, frame = 0, last = 0;
  var pointer = { x: .5, y: .38, tx: .5, ty: .38 };
  var stars = [];
  function resize() {
    var r = hero.getBoundingClientRect();
    w = Math.max(1, r.width); h = Math.max(1, r.height);
    dpr = Math.min(window.devicePixelRatio || 1, 1.6);
    canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    stars = [];
    var n = Math.min(115, Math.round(w * h / 11500));
    for (var i = 0; i < n; i++) stars.push({ x: Math.random() * w, y: Math.random() * h * .72, r: Math.random() * 1.1 + .25, a: Math.random() * .42 + .12, p: Math.random() * 7 });
    draw(performance.now(), true);
  }
  function ribbon(t, index, staticFrame) {
    var base = h * (.31 + index * .054);
    var amp = h * (.055 + index * .012);
    var shift = (pointer.x - .5) * w * .075;
    var lift = (pointer.y - .38) * h * .055;
    var phase = staticFrame ? index * 1.7 : t * (.00013 + index * .000012) + index * 1.7;
    var points = [];
    var steps = 38;
    for (var i = 0; i <= steps; i++) {
      var x = (w * i / steps) + shift;
      var u = i / steps;
      var wave = Math.sin(u * 7.4 + phase) * amp + Math.sin(u * 17 - phase * .72) * amp * .28;
      var y = base + wave + lift + Math.sin(u * 3.2 + phase * .4) * h * .035;
      points.push([x, y]);
    }
    var grad = ctx.createLinearGradient(w * .05, base, w * .97, base + h * .12);
    if (index % 2 === 0) {
      grad.addColorStop(0, 'rgba(25,114,81,0)'); grad.addColorStop(.28, 'rgba(57,202,119,.44)'); grad.addColorStop(.55, 'rgba(132,244,154,.72)'); grad.addColorStop(.78, 'rgba(75,218,190,.48)'); grad.addColorStop(1, 'rgba(36,116,117,0)');
    } else {
      grad.addColorStop(0, 'rgba(39,112,94,0)'); grad.addColorStop(.34, 'rgba(41,174,140,.35)'); grad.addColorStop(.64, 'rgba(114,229,169,.55)'); grad.addColorStop(.86, 'rgba(75,184,184,.3)'); grad.addColorStop(1, 'rgba(49,113,117,0)');
    }
    ctx.beginPath();
    points.forEach(function (p, i) { if (!i) ctx.moveTo(p[0], p[1]); else { var prev = points[i - 1]; ctx.quadraticCurveTo(prev[0], prev[1], (prev[0] + p[0]) / 2, (prev[1] + p[1]) / 2); } });
    ctx.lineTo(w + 80, base + h * .2); ctx.lineTo(-80, base + h * .2); ctx.closePath();
    ctx.fillStyle = grad; ctx.globalAlpha = index < 3 ? .55 : .32; ctx.fill();
    ctx.beginPath();
    points.forEach(function (p, i) { if (!i) ctx.moveTo(p[0], p[1]); else { var prev = points[i - 1]; ctx.quadraticCurveTo(prev[0], prev[1], (prev[0] + p[0]) / 2, (prev[1] + p[1]) / 2); } });
    ctx.strokeStyle = grad; ctx.lineWidth = index < 2 ? 2.4 : 1.2; ctx.globalAlpha = .68; ctx.shadowColor = index % 2 ? '#53d9ad' : '#9df2a5'; ctx.shadowBlur = index < 2 ? 22 : 12; ctx.stroke(); ctx.shadowBlur = 0; ctx.globalAlpha = 1;
  }
  function draw(now, staticFrame) {
    ctx.clearRect(0, 0, w, h);
    pointer.x += (pointer.tx - pointer.x) * .035; pointer.y += (pointer.ty - pointer.y) * .035;
    stars.forEach(function (s) { var twinkle = staticFrame ? 1 : .72 + Math.sin(now * .0006 + s.p) * .28; ctx.fillStyle = 'rgba(209,239,223,' + (s.a * twinkle) + ')'; ctx.beginPath(); ctx.arc(s.x + (pointer.x - .5) * 7, s.y, s.r, 0, Math.PI * 2); ctx.fill(); });
    var glow = ctx.createRadialGradient(w * (.65 + (pointer.x - .5) * .12), h * (.34 + (pointer.y - .38) * .1), 0, w * .65, h * .36, h * .5);
    glow.addColorStop(0, 'rgba(40,143,99,.17)'); glow.addColorStop(1, 'rgba(20,88,77,0)'); ctx.fillStyle = glow; ctx.fillRect(0, 0, w, h);
    ctx.globalCompositeOperation = 'screen';
    for (var i = 0; i < 7; i++) ribbon(now, i, staticFrame);
    ctx.globalCompositeOperation = 'source-over';
    if (!staticFrame && !reduce.matches && document.visibilityState === 'visible') frame = requestAnimationFrame(function (t) { if (t - last > 28) { last = t; draw(t, false); } else frame = requestAnimationFrame(function (tt) { draw(tt, false); }); });
  }
  function onMove(e) { if (!fine.matches) return; var r = hero.getBoundingClientRect(); pointer.tx = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)); pointer.ty = Math.max(0, Math.min(1, (e.clientY - r.top) / r.height)); }
  function start() { if (frame) cancelAnimationFrame(frame); if (reduce.matches || document.visibilityState !== 'visible') draw(performance.now(), true); else { last = 0; frame = requestAnimationFrame(function (t) { draw(t, false); }); } }
  hero.addEventListener('pointermove', onMove, { passive: true });
  hero.addEventListener('pointerleave', function () { pointer.tx = .5; pointer.ty = .38; }, { passive: true });
  window.addEventListener('resize', resize, { passive: true });
  document.addEventListener('visibilitychange', start);
  if (reduce.addEventListener) reduce.addEventListener('change', start);
  if ('IntersectionObserver' in window) { var io = new IntersectionObserver(function (entries) { if (entries[0].isIntersecting) start(); else if (frame) { cancelAnimationFrame(frame); frame = 0; } }); io.observe(hero); }
  var reveals = document.querySelectorAll('[data-reveal]');
  if ('IntersectionObserver' in window && !reduce.matches) { var ro = new IntersectionObserver(function (entries) { entries.forEach(function (entry) { if (entry.isIntersecting) { entry.target.classList.add('seen'); ro.unobserve(entry.target); } }); }, { threshold: .12 }); reveals.forEach(function (el) { ro.observe(el); }); } else { reveals.forEach(function (el) { el.classList.add('seen'); }); }
  resize();
})();
