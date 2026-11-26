/* SearchLens UI - plain JavaScript, no libraries needed */
(function () {
  var root = document.documentElement;

  /* ---------- theme toggle (remembers choice) ---------- */
  try { var saved = localStorage.getItem('sl-theme'); if (saved) root.setAttribute('data-theme', saved); } catch (e) {}
  var themeBtn = document.getElementById('sl-theme');
  if (themeBtn) themeBtn.addEventListener('click', function () {
    var next = root.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
    root.setAttribute('data-theme', next);
    try { localStorage.setItem('sl-theme', next); } catch (e) {}
  });

  /* ---------- mobile menu ---------- */
  var burger = document.getElementById('sl-burger'), links = document.getElementById('sl-links');
  if (burger) burger.addEventListener('click', function () { links.classList.toggle('open'); });

  /* ---------- press "/" to focus the search box ---------- */
  var box = document.querySelector('.sl-search input[name="filename"]');
  document.addEventListener('keydown', function (e) {
    if (e.key === '/' && box && document.activeElement !== box) { e.preventDefault(); box.focus(); }
  });

  /* ---------- recent searches ---------- */
  function getRecent() { try { return JSON.parse(localStorage.getItem('sl-recent') || '[]'); } catch (e) { return []; } }
  function setRecent(a) { try { localStorage.setItem('sl-recent', JSON.stringify(a.slice(0, 6))); } catch (e) {} }
  var form = document.querySelector('.sl-search');
  if (form && box) form.addEventListener('submit', function () {
    var q = box.value.trim(); if (!q) return;
    var list = getRecent().filter(function (x) { return x.toLowerCase() !== q.toLowerCase(); });
    list.unshift(q); setRecent(list);
  });
  var recentBox = document.getElementById('sl-recent');
  if (recentBox) {
    var r = getRecent();
    if (r.length) {
      recentBox.innerHTML = '<small>Recent:</small>';
      r.forEach(function (q) {
        var a = document.createElement('a');
        a.className = 'sl-chip'; a.textContent = q;
        a.href = recentBox.getAttribute('data-url') + '?filename=' + encodeURIComponent(q);
        recentBox.appendChild(a);
      });
      var c = document.createElement('button');
      c.className = 'sl-clear'; c.textContent = 'clear';
      c.onclick = function () { setRecent([]); recentBox.innerHTML = ''; };
      recentBox.appendChild(c);
    }
  }

  /* ---------- background: slow-moving network of nodes (hints at the link graph) ---------- */
  var cv = document.getElementById('sl-bg');
  if (cv && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    var ctx = cv.getContext('2d'), W, H, pts = [], N = 46;
    function size() { W = cv.width = innerWidth; H = cv.height = innerHeight; }
    size(); addEventListener('resize', size);
    for (var i = 0; i < N; i++) pts.push({ x: Math.random() * innerWidth, y: Math.random() * innerHeight,
      vx: (Math.random() - .5) * .25, vy: (Math.random() - .5) * .25, r: 1.5 + Math.random() * 2 });
    (function loop() {
      ctx.clearRect(0, 0, W, H);
      var col = getComputedStyle(root).getPropertyValue('--accent').trim() || '#7c8cff';
      ctx.fillStyle = col; ctx.strokeStyle = col;
      pts.forEach(function (p) {
        p.x += p.vx; p.y += p.vy;
        if (p.x < 0 || p.x > W) p.vx *= -1; if (p.y < 0 || p.y > H) p.vy *= -1;
      });
      for (var a = 0; a < N; a++) {
        for (var b = a + 1; b < N; b++) {
          var dx = pts[a].x - pts[b].x, dy = pts[a].y - pts[b].y, d = Math.sqrt(dx * dx + dy * dy);
          if (d < 140) { ctx.globalAlpha = (1 - d / 140) * .22; ctx.beginPath(); ctx.moveTo(pts[a].x, pts[a].y); ctx.lineTo(pts[b].x, pts[b].y); ctx.stroke(); }
        }
        ctx.globalAlpha = .45; ctx.beginPath(); ctx.arc(pts[a].x, pts[a].y, pts[a].r, 0, 6.3); ctx.fill();
      }
      requestAnimationFrame(loop);
    })();
  }

  /* ---------- tilt effect on feature cards (small 3D touch) ---------- */
  document.querySelectorAll('.sl-feature').forEach(function (el) {
    el.addEventListener('mousemove', function (e) {
      var b = el.getBoundingClientRect(), x = (e.clientX - b.left) / b.width - .5, y = (e.clientY - b.top) / b.height - .5;
      el.style.transform = 'perspective(700px) rotateY(' + (x * 8) + 'deg) rotateX(' + (-y * 8) + 'deg)';
    });
    el.addEventListener('mouseleave', function () { el.style.transform = ''; });
  });

  /* ---------- results page ---------- */
  // fill the search box with what the user searched (read from the URL)
  var q = (new URLSearchParams(location.search).get('filename') || '').trim();
  if (box && q) box.value = q;

  var list = document.getElementById('sl-list');
  if (!list) return;

  var cards = Array.prototype.slice.call(list.querySelectorAll('.sl-card'));

  // 2) highlight the search words (text is escaped first, so file names can never inject HTML)
  var escHtml = function (t) { return t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); };
  var esc = function (t) { return t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); };
  var words = q.replace(/^\/+/, '').split(/\s+/).filter(Boolean).map(esc);
  var rx = words.length ? new RegExp('(' + words.join('|') + ')', 'ig') : null;
  function mark(el) { var t = escHtml(el.textContent); el.innerHTML = rx ? t.replace(rx, '<mark>$1</mark>') : t; }

  var scores = cards.map(function (c) { return parseFloat(c.dataset.score) || 0; });
  var maxS = Math.max.apply(null, scores.concat([1]));
  cards.forEach(function (c, i) {
    c.style.animationDelay = (i * 80) + 'ms';
    var sc = parseFloat(c.dataset.score) || 0, pct = Math.round(sc / maxS * 100);
    mark(c.querySelector('.sl-title'));
    var sn = c.querySelector('.sl-snip'); if (sn) mark(sn);
    setTimeout(function () { c.querySelector('.sl-bar i').style.width = pct + '%'; }, 120);
    c.querySelector('.sl-pct').textContent = pct + '%';
  });

  // 3) "Why this rank?" toggles
  list.addEventListener('click', function (e) {
    if (!e.target.classList.contains('sl-why')) return;
    var d = e.target.closest('.sl-card').querySelector('.sl-detail');
    d.classList.toggle('open');
    e.target.textContent = d.classList.contains('open') ? 'Hide explanation' : 'Why this rank?';
  });

  // 4) sorting + filtering (done in the browser, so it is instant)
  var mode = 'weight';
  function render() {
    var f = (document.getElementById('sl-filter').value || '').toLowerCase(), shown = 0;
    cards.sort(function (a, b) {
      return mode === 'name' ? a.dataset.name.localeCompare(b.dataset.name)
                             : ((parseFloat(b.dataset.score) || 0) - (parseFloat(a.dataset.score) || 0)) ||
                               ((parseFloat(b.dataset.weight) || 0) - (parseFloat(a.dataset.weight) || 0));
    });
    cards.forEach(function (c, i) {
      var ok = c.dataset.name.toLowerCase().indexOf(f) > -1;
      c.style.display = ok ? '' : 'none';
      if (ok) { shown++; c.querySelector('.sl-num').textContent = shown; }
      list.appendChild(c);
    });
    document.getElementById('sl-shown').textContent = shown;
  }
  document.querySelectorAll('.sl-tab').forEach(function (t) {
    t.addEventListener('click', function () {
      document.querySelectorAll('.sl-tab').forEach(function (x) { x.classList.remove('on'); });
      t.classList.add('on'); mode = t.dataset.sort; render();
    });
  });
  document.getElementById('sl-filter').addEventListener('input', render);
  render();
})();
