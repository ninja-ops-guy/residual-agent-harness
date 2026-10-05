/* Deliberately scoped: never clear storage for unrelated same-origin projects. */
(() => {
  const button = document.getElementById('forget-walkthrough');
  const status = document.getElementById('forget-status');
  if (!button || !status) return;
  button.addEventListener('click', () => {
    try {
      localStorage.removeItem('residual.walkthrough.consent.v1');
      localStorage.removeItem('residual.walkthrough.v1');
      status.textContent = 'Saved walkthrough choice and progress removed. VM disks, downloads, and provider records were not deleted.';
    } catch (_) {
      status.textContent = 'Browser storage could not be changed. Use your browser site-data settings; other projects on this origin may be affected.';
    }
  });
})();
