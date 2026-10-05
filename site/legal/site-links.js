/* Mission Control covers the body. Move the static links into its flex layout. */
(() => {
  const footer = document.querySelector('[data-residual-legal]');
  if (!footer || !/\/demo(?:\/index\.html)?\/?$/.test(location.pathname)) return;
  function attach() {
    const control = document.getElementById('mission-control');
    if (!control) return false;
    if (footer.parentElement !== control) control.appendChild(footer);
    return true;
  }
  if (attach()) return;
  const observer = new MutationObserver(() => { if (attach()) observer.disconnect(); });
  observer.observe(document.body, {childList: true, subtree: true});
  window.addEventListener('pagehide', () => observer.disconnect(), {once: true});
})();
