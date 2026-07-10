/* Interactive layer: hover tooltips + department popovers linking into the
   Budget Tracker. Progressive enhancement over the inline SVG; print unaffected. */
(function () {
  var tip = document.getElementById('tip');

  // ---- hover tooltips ----
  if (tip) {
    document.addEventListener('mousemove', function (e) {
      var el = e.target.closest ? e.target.closest('.iv') : null;
      if (el && el.dataset.tip) {
        tip.textContent = el.dataset.tip;
        tip.style.opacity = 1;
        var x = Math.min(e.clientX + 14, window.innerWidth - tip.offsetWidth - 8);
        tip.style.left = x + 'px';
        tip.style.top = (e.clientY + 16) + 'px';
      } else {
        tip.style.opacity = 0;
      }
    });
  }

  // ---- department popover -> Budget Tracker ----
  var LINKS = window.PRIMER_LINKS || {};
  var pop = document.createElement('div');
  pop.id = 'popover';
  pop.className = 'noprint';
  pop.setAttribute('role', 'dialog');
  pop.setAttribute('aria-modal', 'false');
  pop.hidden = true;
  document.body.appendChild(pop);

  function money(n) {
    if (!n) return '$0';
    if (n >= 1e9) return '$' + (n / 1e9).toFixed(2).replace(/\.?0+$/, '') + 'B';
    return '$' + (n / 1e6).toFixed(1).replace(/\.0$/, '') + 'M';
  }

  function show(code, anchor) {
    var d = LINKS[code];
    if (!d) return;
    var stats = '';
    if (d.operating) stats += '<div><span>Operating</span><b>' + money(d.operating) + '</b></div>';
    if (d.capital) stats += '<div><span>Capital</span><b>' + money(d.capital) + '</b></div>';
    if (d.positions) stats += '<div><span>Positions</span><b>' +
      Math.round(d.positions).toLocaleString() + '</b></div>';
    pop.innerHTML =
      '<button class="pop-x" aria-label="Close">×</button>' +
      '<h5>' + d.name + '</h5>' +
      (stats ? '<div class="pop-stats">' + stats + '</div>' : '') +
      '<p>' + d.blurb + '</p>' +
      '<a class="pop-cta" href="' + d.url + '" target="_blank" rel="noopener">' +
      'View in Budget Tracker →</a>';
    pop.hidden = false;
    // position near the anchor, clamped to the viewport
    var r = anchor.getBoundingClientRect();
    var pw = pop.offsetWidth, ph = pop.offsetHeight;
    var x = Math.min(Math.max(r.left + r.width / 2 - pw / 2, 10),
                     window.innerWidth - pw - 10);
    var y = r.bottom + 10;
    if (y + ph > window.innerHeight - 10) y = Math.max(r.top - ph - 10, 10);
    pop.style.left = x + 'px';
    pop.style.top = y + 'px';
    pop.querySelector('.pop-x').focus();
  }

  function hide() { pop.hidden = true; }

  document.addEventListener('click', function (e) {
    if (!pop.hidden && pop.contains(e.target)) {
      if (e.target.classList.contains('pop-x')) hide();
      return;
    }
    var el = e.target.closest ? e.target.closest('[data-dept]') : null;
    if (el) {
      if (tip) tip.style.opacity = 0;
      show(el.dataset.dept, el);
    } else {
      hide();
    }
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') hide();
  });
  window.addEventListener('scroll', hide, {passive: true});
})();
