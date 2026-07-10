/* Tooltip layer for the interactive build — progressive enhancement over inline SVG. */
(function () {
  var tip = document.getElementById('tip');
  if (!tip) return;
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
})();
